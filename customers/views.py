from rest_framework import viewsets, permissions
from .models import Customer
from .serializers import CustomerSerializer
from users.permissions import IsAdminUser, IsUser
from users.models import AuditLog

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsUser]

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAdminUser()]
        return super().get_permissions()

    def perform_create(self, serializer):
        obj = serializer.save()
        AuditLog.objects.create(
            user=self.request.user, 
            action="Created Customer", 
            model_name="Customer", 
            record_id=obj.id, 
            details=f"Name: {obj.full_name}"
        )

    def perform_destroy(self, instance):
        AuditLog.objects.create(
            user=self.request.user, 
            action="Deleted Customer", 
            model_name="Customer", 
            record_id=instance.id, 
            details=f"Name: {instance.full_name}"
        )
        instance.delete()
