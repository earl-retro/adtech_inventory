from paypalcheckoutsdk.core import PayPalHttpClient, SandboxEnvironment, LiveEnvironment
from paypalcheckoutsdk.orders import OrdersCreateRequest, OrdersCaptureRequest
from django.conf import settings

# Initialize PayPal environment
if getattr(settings, 'PAYPAL_MODE', 'sandbox') == 'live':
    environment = LiveEnvironment(
        client_id=settings.PAYPAL_CLIENT_ID,
        client_secret=settings.PAYPAL_CLIENT_SECRET
    )
else:
    environment = SandboxEnvironment(
        client_id=settings.PAYPAL_CLIENT_ID,
        client_secret=settings.PAYPAL_CLIENT_SECRET
    )

client = PayPalHttpClient(environment)

def create_paypal_order(amount):
    """
    Creates a PayPal order using V2 SDK and returns the Order ID.
    This Order ID is explicitly for the React Smart Buttons.
    """
    request = OrdersCreateRequest()
    request.prefer('return=representation')
    request.request_body({
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {
                "currency_code": "PHP",
                "value": str(amount)
            }
        }]
    })

    try:
        response = client.execute(request)
        return {"success": True, "order_id": response.result.id}
    except IOError as ioe:
        if getattr(ioe, "message", None):
            return {"success": False, "error": ioe.message}
        return {"success": False, "error": str(ioe)}
    except Exception as e:
        return {"success": False, "error": str(e)}

def execute_paypal_payment(order_id):
    """
    Captures a PayPal order after it has been approved on the frontend.
    """
    request = OrdersCaptureRequest(order_id)
    try:
        response = client.execute(request)
        if response.result.status == "COMPLETED":
            try:
                capture_id = response.result.purchase_units[0].payments.captures[0].id
            except (IndexError, AttributeError):
                capture_id = response.result.id
            return {"success": True, "capture_id": capture_id}
        else:
            return {"success": False, "error": f"Payment not completed. Status: {response.result.status}"}
    except IOError as ioe:
        if getattr(ioe, "message", None):
            return {"success": False, "error": ioe.message}
        return {"success": False, "error": str(ioe)}
    except Exception as e:
        return {"success": False, "error": str(e)}
