from django.core.files.uploadhandler import StopUpload
from django.http import JsonResponse
from django.conf import settings
import json

class ResponseFormaterMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            # Proceed with the request processing
            response = self.get_response(request)

            # Handle specific status code checks
            if response.status_code == 422:
                json_val = json.loads(response.content)
                print(f'422 - {json_val}')
                item_error = json_val["detail"][0]
                msg = item_error['msg']
    
                return JsonResponse({"detail": msg or "Invalid data passed"}, status=422)
                
            return response

        except StopUpload as e:
            # Catch StopUpload exception and return a custom response
            return JsonResponse({"detail": "Image size is too big"}, status=400)
        
        except Exception as e:
            if settings.DEBUG == True:
                return JsonResponse({"detail": str(e)})
            return JsonResponse({"detail": "Internal server error - internal"})
