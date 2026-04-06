from rest_framework import serializers
from .models import Category, Supplier, Product, StockIn

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True, required=False, allow_null=True
    )
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = '__all__'

class StockInSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )
    supplier_id = serializers.PrimaryKeyRelatedField(
        queryset=Supplier.objects.all(), source='supplier', write_only=True, required=False, allow_null=True
    )
    product = ProductSerializer(read_only=True)
    supplier = SupplierSerializer(read_only=True)

    class Meta:
        model = StockIn
        fields = '__all__'
