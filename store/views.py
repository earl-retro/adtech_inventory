import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from customers.models import Customer
from inventory.models import Category, Product, StockIn, Supplier
from sales.models import Sale, SaleItem
from users.models import AuditLog

from .cart import Cart
from .forms import (CheckoutForm, CustomerForm, LoginForm, ProductForm, StockInForm)


# ─────────────────────────── Auth ────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('store:dashboard')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
        )
        if user:
            login(request, user)
            return redirect('store:dashboard')
        form.add_error(None, 'Invalid username or password.')
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('store:login')


# ──────────────────────────── Dashboard ──────────────────────

@login_required
def dashboard(request):
    """
    Shows different KPI cards and data based on user role.
    Admin gets the 'Control Center' (Operations/Inventory).
    User gets the 'Shopping Hub' (My Orders).
    """
    from django.db.models import F, Sum
    products = Product.objects.filter(is_active=True)

    if request.user.is_admin:
        # Admin: Professional Operational Stats
        low_stock = products.filter(stock_quantity__lte=F('reorder_level'))
        sales = Sale.objects.filter(payment_status='completed')
        total_revenue = sales.aggregate(t=Sum('total'))['t'] or Decimal('0')
        
        # Sales trends for chart
        from django.utils import timezone
        import datetime
        since = timezone.now() - datetime.timedelta(days=30)
        recent_sales_qs = Sale.objects.filter(payment_status='completed', created_at__gte=since)
        sales_by_date = {}
        for s in recent_sales_qs:
            d = s.created_at.strftime('%b %d')
            sales_by_date[d] = float(sales_by_date.get(d, 0)) + float(s.total)
            
        context = {
            'role': 'admin',
            'total_products': products.count(),
            'low_stock_count': low_stock.count(),
            'total_revenue': total_revenue,
            'recent_sales': Sale.objects.order_by('-created_at')[:5],
            'low_stock_items': low_stock[:5],
            'sales_chart_labels': json.dumps(list(sales_by_date.keys())),
            'sales_chart_data': json.dumps(list(sales_by_date.values())),
        }
    else:
        # User: Personal Shopping Stats
        user_orders = Sale.objects.filter(user=request.user).order_by('-created_at')
        context = {
            'role': 'user',
            'my_orders_count': user_orders.count(),
            'recent_sales': user_orders[:5],
        }
    
    return render(request, 'dashboard.html', context)


# ──────────────────────────── Catalog ────────────────────────

@login_required
def catalog(request):
    if request.user.is_admin:
        messages.info(request, 'Product Catalog is for customers only. Please manage inventory here.')
        return redirect('store:inventory')
    products = Product.objects.filter(is_active=True).select_related('category')
    categories = Category.objects.all()

    q = request.GET.get('q', '').strip()
    cat = request.GET.get('category', '')

    if q:
        products = products.filter(name__icontains=q) | products.filter(brand__icontains=q)
    if cat:
        products = products.filter(category__id=cat)

    return render(request, 'catalog.html', {
        'products': products,
        'categories': categories,
        'q': q,
        'selected_cat': cat,
    })


@login_required
def product_detail(request, pk):
    if request.user.is_admin:
        return redirect('store:inventory')
    product = get_object_or_404(Product, pk=pk, is_active=True)
    return render(request, 'product_detail.html', {'product': product})


# ──────────────────────────── Cart ───────────────────────────

@login_required
@require_POST
def cart_add(request, pk):
    if request.user.is_admin:
        return redirect('store:dashboard')
    product = get_object_or_404(Product, pk=pk, is_active=True)
    cart = Cart(request)
    quantity = int(request.POST.get('quantity', 1))
    update = request.POST.get('update') == 'true'
    cart.add(product, quantity=quantity, update_quantity=update)
    messages.success(request, f'"{product.name}" updated in cart.')
    next_url = request.POST.get('next', 'store:catalog')
    return redirect(next_url)


@login_required
@require_POST
def cart_remove(request, pk):
    if request.user.is_admin:
        return redirect('store:dashboard')
    cart = Cart(request)
    cart.remove(pk)
    return redirect('store:cart')


@login_required
def cart_view(request):
    if request.user.is_admin:
        return redirect('store:dashboard')
    cart = Cart(request)
    return render(request, 'cart.html', {'cart': cart})


# ──────────────────────────── Checkout ───────────────────────

@login_required
def checkout(request):
    if request.user.is_admin:
        return redirect('store:dashboard')
    cart = Cart(request)
    if cart.is_empty():
        messages.warning(request, 'Your cart is empty.')
        return redirect('store:catalog')

    form = CheckoutForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        # All orders are PayPal in this pure eCommerce model.
        # Store form data in session for the PayPal capture step.
        request.session['checkout_form'] = form.cleaned_data
        request.session['checkout_form']['email'] = str(form.cleaned_data.get('email', '') or '')
        return render(request, 'checkout.html', {
            'form': form,
            'cart': cart,
            'paypal_client_id': _get_paypal_client_id(),
            'cart_total': str(cart.get_total_price()),
        })

    return render(request, 'checkout.html', {
        'form': form,
        'cart': cart,
        'paypal_client_id': _get_paypal_client_id(),
        'cart_total': str(cart.get_total_price()),
    })


def _get_paypal_client_id():
    from django.conf import settings
    return getattr(settings, 'PAYPAL_CLIENT_ID', '')


def _create_sale_from_cart(request, form_data, cart, payment_method, payment_status='completed'):
    """Create a Customer + Sale + SaleItems from cart and form data."""
    customer, _ = Customer.objects.get_or_create(
        email=form_data.get('email') or None,
        defaults={
            'full_name': form_data['full_name'],
            'contact_number': form_data.get('contact_number', ''),
            'address': form_data.get('address', ''),
        }
    )
    if not customer.full_name:
        customer.full_name = form_data['full_name']
        customer.save()

    sale = Sale.objects.create(
        user=request.user,
        customer=customer,
        payment_method=payment_method,
        payment_status=payment_status,
        notes=form_data.get('notes', ''),
        total=Decimal('0'),
    )
    total = Decimal('0')
    for item in cart:
        product = item['product']
        qty = item['quantity']
        if product.stock_quantity < qty:
            raise ValueError(f'Not enough stock for {product.name}')
        SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=qty,
            unit_price=item['price'],
        )
        product.stock_quantity -= qty
        product.save(update_fields=['stock_quantity'])
        total += item['total_price']
    sale.total = total
    sale.save(update_fields=['total'])
    return sale


# ────────────────── PayPal AJAX helpers ──────────────────────

@login_required
def paypal_create_order(request):
    """Called by PayPal JS SDK to get an orderID."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    cart = Cart(request)
    if cart.is_empty():
        return JsonResponse({'error': 'Cart is empty'}, status=400)
    from sales.paypal import create_paypal_order
    result = create_paypal_order(cart.get_total_price())
    if result['success']:
        return JsonResponse({'orderID': result['order_id']})
    return JsonResponse({'error': result['error']}, status=400)


@login_required
def paypal_capture_order(request):
    """Called by PayPal JS SDK after buyer approves payment."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        body = json.loads(request.body)
        order_id = body.get('orderID')
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    from sales.paypal import execute_paypal_payment
    result = execute_paypal_payment(order_id)
    if not result['success']:
        return JsonResponse({'error': result['error']}, status=400)

    cart = Cart(request)
    form_data = request.session.get('checkout_form', {})
    if not form_data.get('full_name'):
        form_data['full_name'] = 'Guest'
        form_data['payment_method'] = 'paypal'

    try:
        with transaction.atomic():
            sale = _create_sale_from_cart(request, form_data, cart, 'paypal', 'completed')
            sale.paypal_order_id = order_id
            sale.paypal_capture_id = result.get('capture_id', '')
            sale.save(update_fields=['paypal_order_id', 'paypal_capture_id'])
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)

    cart.clear()
    if 'checkout_form' in request.session:
        del request.session['checkout_form']

    return JsonResponse({'success': True, 'sale_id': sale.pk})


# ──────────────────────────── Order Confirm ──────────────────

@login_required
def order_confirm(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    # Security: Standard users can only view their own receipts
    if not request.user.is_admin and sale.user != request.user:
        messages.error(request, "Access denied. You can only view your own receipts.")
        return redirect('store:order_list')
    return render(request, 'order_confirm.html', {'sale': sale})


@login_required
def order_list(request):
    if request.user.is_admin:
        sales = Sale.objects.select_related('customer', 'user').order_by('-created_at')
    else:
        sales = Sale.objects.filter(user=request.user).select_related('customer', 'user').order_by('-created_at')
    return render(request, 'order_list.html', {'sales': sales})


# ──────────────────────────── Inventory ──────────────────────

@login_required
def inventory(request):
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Operations are for admins only.')
        return redirect('store:dashboard')
    from django.db.models import F
    products = Product.objects.select_related('category').order_by('name')
    low_ids = set(products.filter(stock_quantity__lte=F('reorder_level')).values_list('id', flat=True))
    return render(request, 'inventory.html', {'products': products, 'low_ids': low_ids})


@login_required
def stock_in(request):
    if not request.user.is_admin:
        messages.error(request, "Access denied. Only Admins can manage stock.")
        return redirect('store:dashboard')
    form = StockInForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        product = form.cleaned_data['product']
        qty = form.cleaned_data['quantity_added']
        supplier = form.cleaned_data.get('supplier')
        StockIn.objects.create(product=product, supplier=supplier, quantity_added=qty)
        product.stock_quantity += qty
        product.save(update_fields=['stock_quantity'])
        AuditLog.objects.create(
            user=request.user,
            action='Stock In',
            model_name='Product',
            record_id=product.id,
            details=f'Added {qty} units. Supplier: {supplier}',
        )
        messages.success(request, f'Added {qty} units of "{product.name}".')
        return redirect('store:inventory')
    return render(request, 'stock_in.html', {'form': form})


@login_required
def product_create(request):
    if not request.user.is_admin:
        messages.error(request, 'Admin access required.')
        return redirect('store:dashboard')
    
    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        product = form.save()
        AuditLog.objects.create(
            user=request.user,
            action='Created Product',
            model_name='Product',
            record_id=product.id,
            details=f'Name: {product.name}, Initial Stock: {product.stock_quantity}',
        )
        messages.success(request, f'Product "{product.name}" created successfully.')
        return redirect('store:inventory')
    
    return render(request, 'product_form.html', {
        'form': form,
        'title': 'Add New Product',
        'is_edit': False
    })


@login_required
def product_edit(request, pk):
    if not request.user.is_admin:
        messages.error(request, 'Admin access required.')
        return redirect('store:dashboard')
    
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        AuditLog.objects.create(
            user=request.user,
            action='Updated Product',
            model_name='Product',
            record_id=product.id,
            details=f'Updated product details for "{product.name}"',
        )
        messages.success(request, f'Product "{product.name}" updated successfully.')
        return redirect('store:inventory')
    
    return render(request, 'product_form.html', {
        'form': form,
        'product': product,
        'title': f'Edit Product: {product.name}',
        'is_edit': True
    })


@login_required
@require_POST
def product_delete(request, pk):
    if not request.user.is_admin:
        messages.error(request, 'Admin access required.')
        return redirect('store:dashboard')
    
    product = get_object_or_404(Product, pk=pk)
    product_name = product.name
    product.delete()
    AuditLog.objects.create(
        user=request.user,
        action='Deleted Product',
        model_name='Product',
        record_id=pk,
        details=f'Deleted product: {product_name}',
    )
    messages.success(request, f'Product "{product_name}" deleted.')
    return redirect('store:inventory')


# ──────────────────────────── Customers ──────────────────────

@login_required
def customers(request):
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('store:dashboard')
    all_customers = Customer.objects.order_by('full_name')
    return render(request, 'customers.html', {'customers': all_customers})


@login_required
def customer_create(request):
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('store:dashboard')
    form = CustomerForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Customer created.')
        return redirect('store:customers')
    return render(request, 'customer_form.html', {'form': form, 'title': 'New Customer'})


# ──────────────────────────── Reports ────────────────────────

@login_required
def reports(request):
    if not request.user.is_admin:
        messages.error(request, 'Admin access required.')
        return redirect('store:dashboard')

    from django.db.models import Sum
    sales = Sale.objects.filter(payment_status='completed')
    total_revenue = sales.aggregate(t=Sum('total'))['t'] or Decimal('0')
    by_method = {
        'cash': float(sales.filter(payment_method='cash').aggregate(t=Sum('total'))['t'] or 0),
        'paypal': float(sales.filter(payment_method='paypal').aggregate(t=Sum('total'))['t'] or 0),
    }
    return render(request, 'reports.html', {
        'total_revenue': total_revenue,
        'total_orders': sales.count(),
        'by_method': json.dumps(by_method),
        'recent_sales': sales.order_by('-created_at')[:10],
    })
