from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Sale
from .serializers import SaleSerializer
from .paypal import create_paypal_order, execute_paypal_payment
from django.db import transaction
from users.permissions import IsAdminUser, IsUser
from users.models import AuditLog

class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    filterset_fields = ['customer', 'payment_status', 'payment_method']
    permission_classes = [IsUser]

    def get_permissions(self):
        if self.action in ['destroy', 'update', 'partial_update']:
            return [IsAdminUser()]
        return super().get_permissions()

    def perform_create(self, serializer):
        with transaction.atomic():
            sale = serializer.save(user=self.request.user)
            # Payment completion is managed automatically based on payment method
            if sale.payment_method in ['cash', 'gcash']:
                sale.payment_status = 'completed'
                sale.save()
            
            AuditLog.objects.create(
                user=self.request.user, 
                action="Processed Sale", 
                model_name="Sale", 
                record_id=sale.id, 
                details=f"Total: {sale.total}, Method: {sale.payment_method}"
            )

    @action(detail=True, methods=['post'])
    def create_paypal_payment(self, request, pk=None):
        sale = self.get_object()
        if sale.payment_method != 'paypal':
            return Response({"error": "Payment method is not PayPal"}, status=status.HTTP_400_BAD_REQUEST)
        
        result = create_paypal_order(sale.total)
        
        if result['success']:
            sale.paypal_order_id = result['order_id']
            sale.save()
            return Response({"orderID": result['order_id']})
        else:
            return Response({"error": result['error']}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def capture_paypal_payment(self, request, pk=None):
        sale = self.get_object()
        order_id = request.data.get('orderID')
        
        if not order_id:
            return Response({"error": "orderID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        if sale.payment_status == 'completed':
            return Response({"error": "Payment already completed"}, status=status.HTTP_400_BAD_REQUEST)
        
        result = execute_paypal_payment(order_id)
        
        if result['success']:
            with transaction.atomic():
                sale.payment_status = 'completed'
                sale.paypal_capture_id = result['capture_id']
                sale.save()
                
                # Now deduct stock
                for item in sale.items.all():
                    product = item.product
                    if product.stock_quantity >= item.quantity:
                        product.stock_quantity -= item.quantity
                        product.save()
                    else:
                        return Response({"error": f"Not enough stock for {product.name} after payment."}, status=status.HTTP_400_BAD_REQUEST)
            
            AuditLog.objects.create(user=self.request.user, action="Captured PayPal V2", model_name="Sale", record_id=sale.id, details=f"Capture ID: {sale.paypal_capture_id}")
            return Response({"success": True, "sale": SaleSerializer(sale).data})
        else:
            sale.payment_status = 'failed'
            sale.save()
            return Response({"error": result['error']}, status=status.HTTP_400_BAD_REQUEST)
