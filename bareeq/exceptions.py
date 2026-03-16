from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.db import IntegrityError


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None and isinstance(exc, IntegrityError):
        return Response(
            {"message": "Database conflict: This data already exists."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if response is not None:
        error_data = response.data
        final_message = "An error occurred."

        if isinstance(error_data, dict):
            try:
                first_field = next(iter(error_data))
                first_error = error_data[first_field]

                if isinstance(first_error, list):
                    first_error = first_error[0]

                translations = {
                    "Invalid email/phone or password.": "بيانات الدخول غير صحيحة",
                    "هذا الاسم مستخدم بالفعل": "Username is already taken",
                    "هذا البريد الإلكتروني مسجل مسبقاً": "Email is already registered",
                    "رقم الهاتف هذا مسجل مسبقاً": "Phone number is already registered",
                    "كلمة المرور الحالية غير صحيحة": "كلمة المرور الحالية غير صحيحة",
                }

                clean_error = translations.get(
                    str(first_error), str(first_error))

                if first_field == 'non_field_errors':
                    final_message = clean_error
                else:
                    final_message = f"{first_field}: {clean_error}"

            except (StopIteration, KeyError, IndexError):
                final_message = "Validation error occurred."

        response.data = {"message": final_message}

    return response
