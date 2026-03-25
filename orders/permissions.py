from rest_framework import permissions


class IsVendorEmployee(permissions.BasePermission):
    """
    Allows access only to Vendors or their Employees.
    """

    def has_permission(self, request, view):
        # Must be logged in and have a profile
        if not (request.user and request.user.is_authenticated and hasattr(request.user, 'profile')):
            return False

        role = request.user.profile.role.upper()
        # Return True if they are either the Vendor or an Employee
        return role in ['VENDOR', 'EMPLOYEE']
