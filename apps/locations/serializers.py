# ══════════════════════════════════════════════════════════════════════════
# apps/locations/serializers.py
# ══════════════════════════════════════════════════════════════════════════
from rest_framework import serializers
from .models import Location


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Location
        fields = [
            'id', 'name', 'city', 'country', 'country_code',
            'state', 'latitude', 'longitude', 'timezone',
            'is_default', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class LocationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Location
        fields = ['name', 'city', 'country', 'country_code', 'state',
                  'latitude', 'longitude', 'timezone', 'is_default']

    def create(self, validated_data):
        user = self.context['request'].user if self.context['request'].user.is_authenticated else None
        validated_data['user'] = user
        return super().create(validated_data)