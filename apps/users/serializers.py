# ══════════════════════════════════════════════════════════════════════════
# apps/users/serializers.py
# ══════════════════════════════════════════════════════════════════════════
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserPreferences

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password  = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, label='Confirm password')

    class Meta:
        model  = User
        fields = ['email', 'username', 'password', 'password2']

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(
            email    = validated_data['email'],
            username = validated_data['username'],
            password = validated_data['password'],
        )
        UserPreferences.objects.create(user=user)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['id', 'email', 'username', 'date_joined']
        read_only_fields = fields


class UserPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model  = UserPreferences
        fields = [
            'units', 'language', 'push_alerts',
            'alert_severity', 'fcm_token',
            'location_consent', 'data_retention_days',
        ]