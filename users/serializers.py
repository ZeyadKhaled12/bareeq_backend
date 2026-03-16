
from .models import TimeSlot
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
import re
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.validators import UniqueValidator
from .models import UserProfile
from lists.models import Gender
from django.db.models import Q
from django.contrib.auth import authenticate


class CustomerRegistrationSerializer(serializers.ModelSerializer):
    # 1. Username Unique Check
    username = serializers.CharField(
        required=True,
        validators=[UniqueValidator(
            queryset=User.objects.all(), message="هذا الاسم مستخدم بالفعل")]
    )

    # 2. Email Format & Unique Check
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all(
        ), message="هذا البريد الإلكتروني مسجل مسبقاً")]
    )

    # 3. Password Strength
    password = serializers.CharField(write_only=True, required=True)

    # 4. Profile Fields (Write Only)
    phone = serializers.CharField(
        write_only=True,
        required=True,
        validators=[UniqueValidator(
            queryset=UserProfile.objects.all(), message="رقم الهاتف هذا مسجل مسبقاً")]
    )
    gender = serializers.PrimaryKeyRelatedField(
        queryset=Gender.objects.all(),
        write_only=True,
        required=True
    )
    date_of_birth = serializers.DateField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'email',
                  'phone', 'gender', 'date_of_birth']

    # --- CUSTOM VALIDATIONS ---

    def validate_password(self, value):
        """Checks if password meets Django security standards."""
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate_phone(self, value):
        """Checks if phone number format is correct (e.g., Egyptian format)."""
        if not re.match(r'^(010|011|012|015)\d{8}$', value):
            raise serializers.ValidationError(
                "رقم الهاتف غير صحيح. يجب أن يبدأ بـ 010 أو 011 أو 012 أو 015")
        return value

    def create(self, validated_data):
        # Extract profile data
        phone = validated_data.pop('phone')
        gender = validated_data.pop('gender')
        dob = validated_data.pop('date_of_birth')

        # Create User
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )

        # Create Profile
        UserProfile.objects.create(
            user=user,
            role='CUSTOMER',
            phone=phone,
            gender=gender,
            date_of_birth=dob
        )
        return user

    def to_representation(self, instance):
        # Get the standard User fields (id, username, email)
        representation = super().to_representation(instance)

        # Access the profile
        profile = getattr(instance, 'profile', None)
        if profile:
            # Add profile fields directly to the top level
            representation['phone'] = profile.phone
            representation['gender'] = profile.gender.id if profile.gender else None
            representation['date_of_birth'] = profile.date_of_birth
            representation['role'] = profile.role

        return representation


class LoginSerializer(serializers.Serializer):
    # We use 'login_id' to accept either email or phone
    login_id = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        login_id = data.get('login_id')
        password = data.get('password')

        # 1. Find the user by Email OR by Phone (inside UserProfile)
        user = User.objects.filter(
            Q(email=login_id) | Q(profile__phone=login_id)
        ).first()

        # 2. Check if user exists and password is correct
        if user and user.check_password(password):
            if not user.is_active:
                raise serializers.ValidationError("This account is disabled.")
            return user

        raise serializers.ValidationError("Invalid email/phone or password.")


# users/serializers.py


# users/serializers.py

class CustomerUpdateSerializer(serializers.ModelSerializer):
    # Map the flat fields to the nested profile model
    phone = serializers.CharField(source='profile.phone')
    gender = serializers.PrimaryKeyRelatedField(
        source='profile.gender',
        queryset=Gender.objects.all()
    )
    date_of_birth = serializers.DateField(source='profile.date_of_birth')

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'gender', 'date_of_birth']

    def validate_username(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(username=value).exists():
            raise serializers.ValidationError("هذا الاسم مستخدم بالفعل")
        return value

    def validate_phone(self, value):
        if not re.match(r'^(010|011|012|015)\d{8}$', value):
            raise serializers.ValidationError("رقم الهاتف غير صحيح")
        user = self.context['request'].user
        if UserProfile.objects.exclude(user=user).filter(phone=value).exists():
            raise serializers.ValidationError("رقم الهاتف هذا مسجل مسبقاً")
        return value

    def update(self, instance, validated_data):
        # Extract the profile data nested by the 'source' dots
        profile_data = validated_data.pop('profile', {})

        # Update User fields
        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)
        instance.save()

        # Update Profile fields
        profile = instance.profile
        profile.phone = profile_data.get('phone', profile.phone)
        profile.gender = profile_data.get('gender', profile.gender)
        profile.date_of_birth = profile_data.get(
            'date_of_birth', profile.date_of_birth)
        profile.save()

        return instance

    def to_representation(self, instance):
        # Reuse your registration serializer for the response to keep it consistent and flat
        return CustomerRegistrationSerializer(instance).data


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                "confirm_password": "كلمات المرور الجديدة غير متطابقة"
            })
        return data


User = get_user_model()


class VendorRegisterSerializer(serializers.ModelSerializer):
    # We use 'phone' as the input, but it maps to 'username' in the database
    phone = serializers.CharField(source='username', required=True)
    full_name = serializers.CharField(source='first_name', required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['phone', 'email', 'full_name', 'password']

    def validate_phone(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("هذا الرقم مسجل مسبقاً")
        if not re.match(r'^01[0125][0-9]{8}$', value):
            raise serializers.ValidationError("يرجى إدخال رقم هاتف مصري صحيح")
        return value

    def create(self, validated_data):
        # Because of source='username', phone is already in 'username'
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name']
        )
        UserProfile.objects.create(
            user=user, role='VENDOR', phone=validated_data['username'])
        return user

    def to_representation(self, instance):
        refresh = RefreshToken.for_user(instance)
        return {
            'user': {
                'full_name': instance.first_name,
                'email': instance.email,
                'phone': instance.profile.phone,
            },
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }


class VendorProfileSerializer(serializers.ModelSerializer):
    # This maps 'phone' in JSON to 'username' in the User model
    phone = serializers.CharField(source='username')
    full_name = serializers.CharField(source='first_name')

    class Meta:
        model = User
        fields = ['phone', 'email', 'full_name']

    def validate_phone(self, value):
        user = self.instance
        if User.objects.exclude(pk=user.pk).filter(username=value).exists():
            raise serializers.ValidationError("رقم الهاتف هذا مسجل لحساب آخر")
        return value

    def update(self, instance, validated_data):
        # Update User model
        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)
        instance.first_name = validated_data.get(
            'first_name', instance.first_name)
        instance.save()

        # Sync the profile model phone number
        profile = instance.profile
        profile.phone = instance.username
        profile.save()

        return instance


class UserProfileSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(source='profile.phone', read_only=True)
    role = serializers.CharField(source='profile.role', read_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'role']


class VendorAuthResponseSerializer(serializers.Serializer):
    """
    Documentation-only serializer to define the Swagger response shape.
    """
    class UserDataSerializer(serializers.Serializer):
        full_name = serializers.CharField()
        email = serializers.EmailField()
        phone = serializers.CharField()
        role = serializers.CharField()

    user = UserDataSerializer()
    access = serializers.CharField()
    refresh = serializers.CharField()


# 1. Handles the individual slot details


class TimeSlotDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeSlot
        fields = ['slots', 'is_free', 'unlimit_orders',
                  'limit_orders', 'is_close']

# 2. Handles the overall structure (Monday -> Receipt -> List of slots)


class VendorTimeSlotResponseSerializer(serializers.Serializer):
    def to_representation(self, instance):
        # instance is the Vendor (User object)
        days = ['monday', 'tuesday', 'wednesday',
                'thursday', 'friday', 'saturday', 'sunday']
        response = {}

        for day in days:
            response[day] = {
                "receipt": TimeSlotDetailSerializer(
                    instance.time_slots.filter(day=day, slot_type='receipt'), many=True
                ).data,
                "delivery": TimeSlotDetailSerializer(
                    instance.time_slots.filter(day=day, slot_type='delivery'), many=True
                ).data,
            }
        return response


# 1. The individual slot details
class TimeSlotRequestItemSerializer(serializers.Serializer):
    slot = serializers.CharField(help_text="e.g. 09:00-11:00")
    is_free = serializers.BooleanField(default=False)
    unlimit_orders = serializers.BooleanField(default=False)
    limit_orders = serializers.IntegerField(default=0)
    is_close = serializers.BooleanField(default=False)
# 1. The individual slot details (NOW WITH ID)


class TimeSlotItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeSlot
        # We include 'id' so the frontend can reference it for orders
        fields = ['id', 'slot', 'is_free',
                  'unlimit_orders', 'limit_orders', 'is_close']

# 2. Grouping for Receipt and Delivery


class DayScheduleSerializer(serializers.Serializer):
    receipt = TimeSlotItemSerializer(many=True)
    delivery = TimeSlotItemSerializer(many=True)

# 3. The Full Week Structure


class TimeSlotBulkUpdateSerializer(serializers.Serializer):
    monday = DayScheduleSerializer()
    tuesday = DayScheduleSerializer()
    wednesday = DayScheduleSerializer()
    thursday = DayScheduleSerializer()
    friday = DayScheduleSerializer()
    saturday = DayScheduleSerializer()
    sunday = DayScheduleSerializer()


class VendorTimeSlotResponseSerializer(serializers.Serializer):
    def to_representation(self, instance):
        """
        instance is the User (Vendor) object.
        We group their time_slots by day and type.
        """
        days = ['monday', 'tuesday', 'wednesday',
                'thursday', 'friday', 'saturday', 'sunday']
        response = {}

        for day in days:
            response[day] = {
                "receipt": TimeSlotItemSerializer(
                    instance.time_slots.filter(day=day, slot_type='receipt'),
                    many=True
                ).data,
                "delivery": TimeSlotItemSerializer(
                    instance.time_slots.filter(day=day, slot_type='delivery'),
                    many=True
                ).data,
            }
        return response
