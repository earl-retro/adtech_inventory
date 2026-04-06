from rest_framework import serializers
from .models import Sale, SaleItem
from inventory.serializers import ProductSerializer
from inventory.models import Product
from customers.serializers import CustomerSerializer
from customers.models import Customer
from django.db import transaction

class SaleItemSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )
    product = ProductSerializer(read_only=True)
    
    class Meta:
        model = SaleItem
        fields = ['id', 'product_id', 'product', 'quantity', 'unit_price', 'subtotal']
        read_only_fields = ['unit_price']

class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True)
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(), source='customer', write_only=True, required=False, allow_null=True
    )
    customer = CustomerSerializer(read_only=True)

    class Meta:
        model = Sale
        fields = '__all__'
        read_only_fields = ['total', 'user', 'payment_status', 'paypal_order_id', 'paypal_capture_id']

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        
        # Calculate initial total based on requested quantities and current product prices
        sale = Sale.objects.create(**validated_data)
        
        total = 0
        for item_data in items_data:
            product = item_data['product']
            quantity = item_data['quantity']
            
            if product.stock_quantity < quantity:
                raise serializers.ValidationError(f"Not enough stock for {product.name}")
                
            unit_price = product.selling_price
            
            # Create SaleItem
            SaleItem.objects.create(
                sale=sale,
                product=product,
                quantity=quantity,
                unit_price=unit_price
            )
            
            # We don't deduct stock here for PayPal until payment completes.
            if sale.payment_method != 'paypal':
                product.stock_quantity -= quantity
                product.save()
            
            total += unit_price * quantity
            
        sale.total = total - getattr(sale, 'discount', 0)
        
        if sale.payment_method in ['cash', 'gcash']:
            sale.payment_status = 'completed'
            
        sale.save()
        return sale
