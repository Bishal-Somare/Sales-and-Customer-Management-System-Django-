from django.db import IntegrityError
from django.shortcuts import render


class IntegrityErrorMiddleware:
    """
    Middleware to catch IntegrityError exceptions throughout the project
    and render an error template.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, IntegrityError):
            # Extract object information if available
            obj_name = None
            if hasattr(exception, 'args') and len(exception.args) > 0:
                error_msg = str(exception.args[0])
                # Try to get a more user-friendly error message
                if "foreign key constraint" in error_msg.lower():
                    obj_name = error_msg.split("REFERENCES")[1].split("(")[0].strip() if "REFERENCES" in error_msg else None
            
            context = {
                'error_message': "This item cannot be deleted because it is referenced by other items in the system.",
                'obj_name': obj_name,
                'detailed_error': str(exception)
            }
            
            return render(request, 'accounts/integrity_error.html', context)
        
        # For other exceptions, let Django handle them
        return None
    


#handling 404 error
