from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import F
from .models import Category, Supplier, Product, StockIn
from .serializers import CategorySerializer, SupplierSerializer, ProductSerializer, StockInSerializer
from users.permissions import IsAdminUser, IsUser, IsAdminOrReadOnly
from users.models import AuditLog

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]

    def perform_create(self, serializer):
        obj = serializer.save()
        AuditLog.objects.create(user=self.request.user, action="Created Category", model_name="Category", record_id=obj.id, details=f"Name: {obj.name}")

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAdminOrReadOnly]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filterset_fields = ['category', 'brand', 'is_active']
    permission_classes = [IsAdminOrReadOnly]

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        low_stock_items = self.get_queryset().filter(stock_quantity__lte=F('reorder_level'))
        serializer = self.get_serializer(low_stock_items, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        obj = serializer.save()
        AuditLog.objects.create(user=self.request.user, action="Created Product", model_name="Product", record_id=obj.id, details=f"Name: {obj.name}, Price: {obj.selling_price}")

    def perform_update(self, serializer):
        obj = serializer.save()
        AuditLog.objects.create(user=self.request.user, action="Updated Product", model_name="Product", record_id=obj.id, details=f"Update by {self.request.user.username}")

    def perform_destroy(self, instance):
        AuditLog.objects.create(user=self.request.user, action="Deleted Product", model_name="Product", record_id=instance.id, details=f"Name: {instance.name}")
        instance.delete()

class StockInViewSet(viewsets.ModelViewSet):
    queryset = StockIn.objects.all()
    serializer_class = StockInSerializer
    filterset_fields = ['product', 'supplier']
    permission_classes = [IsUser] # Both user and admin can add stock

    def perform_create(self, serializer):
        stock_in = serializer.save()
        product = stock_in.product
        product.stock_quantity += stock_in.quantity_added
        product.save()
        AuditLog.objects.create(user=self.request.user, action="Added Stock", model_name="StockIn", record_id=stock_in.id, details=f"Product: {product.name}, Added: {stock_in.quantity_added}")
