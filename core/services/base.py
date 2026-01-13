"""
Base service class for common CRUD operations.

Provides a foundation for domain-specific services with generic
database operations using Django ORM.
"""

from __future__ import annotations

import logging
from typing import Generic, List, Optional, Type, TypeVar

from django.db.models import Model, QuerySet

ModelType = TypeVar("ModelType", bound=Model)

logger = logging.getLogger(__name__)


class BaseService(Generic[ModelType]):
    """
    Generic base service class for common CRUD operations.

    Provides standard database operations that can be inherited by
    domain-specific services like LeaseService, TenantService, etc.

    Example usage:
        class LeaseService(BaseService[Lease]):
            model = Lease

            # Add domain-specific methods
            def generate_contract(self, lease: Lease) -> str:
                ...
    """

    model: Type[ModelType]

    def __init__(self) -> None:
        """Initialize service with logger."""
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_queryset(self) -> QuerySet[ModelType]:
        """
        Get the base queryset for this service.

        Returns:
            QuerySet for the model

        Examples:
            >>> service = LeaseService()
            >>> queryset = service.get_queryset()
            >>> active_leases = queryset.filter(contract_generated=True)
        """
        return self.model.objects.all()

    def get_by_id(self, pk: int) -> Optional[ModelType]:
        """
        Retrieve an object by its primary key.

        Args:
            pk: Primary key of the object

        Returns:
            Model instance if found, None otherwise

        Examples:
            >>> service = LeaseService()
            >>> lease = service.get_by_id(1)
            >>> if lease:
            ...     print(lease.rental_value)
        """
        try:
            instance = self.get_queryset().get(pk=pk)
            self.logger.debug(f"Retrieved {self.model.__name__} with id {pk}")
            return instance
        except self.model.DoesNotExist:
            self.logger.warning(f"{self.model.__name__} with id {pk} not found")
            return None

    def get_all(self) -> List[ModelType]:
        """
        Get all objects.

        Returns:
            List of all model instances

        Examples:
            >>> service = LeaseService()
            >>> all_leases = service.get_all()
            >>> print(f"Total leases: {len(all_leases)}")
        """
        instances = list(self.get_queryset())
        self.logger.debug(f"Retrieved {len(instances)} {self.model.__name__} instances")
        return instances

    def create(self, **kwargs) -> ModelType:
        """
        Create a new object.

        Args:
            **kwargs: Field values for the new object

        Returns:
            Created model instance

        Examples:
            >>> service = TenantService()
            >>> tenant = service.create(
            ...     name="John Doe",
            ...     cpf_cnpj="12345678901",
            ...     phone="11999999999"
            ... )
        """
        instance = self.model(**kwargs)
        instance.save()
        self.logger.info(f"Created {self.model.__name__} with id {instance.pk}")
        return instance

    def update(self, instance: ModelType, **kwargs) -> ModelType:
        """
        Update an existing object.

        Args:
            instance: Model instance to update
            **kwargs: Field values to update

        Returns:
            Updated model instance

        Examples:
            >>> service = LeaseService()
            >>> lease = service.get_by_id(1)
            >>> updated_lease = service.update(lease, due_day=15)
        """
        for field, value in kwargs.items():
            setattr(instance, field, value)
        instance.save()
        self.logger.info(f"Updated {self.model.__name__} with id {instance.pk}")
        return instance

    def delete(self, instance: ModelType) -> None:
        """
        Delete an object.

        Args:
            instance: Model instance to delete

        Examples:
            >>> service = LeaseService()
            >>> lease = service.get_by_id(1)
            >>> service.delete(lease)
        """
        pk = instance.pk
        instance.delete()
        self.logger.info(f"Deleted {self.model.__name__} with id {pk}")

    def exists(self, pk: int) -> bool:
        """
        Check if an object exists by primary key.

        Args:
            pk: Primary key to check

        Returns:
            True if object exists, False otherwise

        Examples:
            >>> service = LeaseService()
            >>> if service.exists(1):
            ...     print("Lease exists")
        """
        exists = self.get_queryset().filter(pk=pk).exists()
        self.logger.debug(f"{self.model.__name__} with id {pk} exists: {exists}")
        return exists

    def count(self) -> int:
        """
        Count total number of objects.

        Returns:
            Total count of model instances

        Examples:
            >>> service = LeaseService()
            >>> total = service.count()
            >>> print(f"Total leases: {total}")
        """
        count = self.get_queryset().count()
        self.logger.debug(f"Total {self.model.__name__} count: {count}")
        return count

    def filter(self, **kwargs) -> List[ModelType]:
        """
        Filter objects by field values.

        Args:
            **kwargs: Field filters (e.g., contract_generated=True)

        Returns:
            List of filtered model instances

        Examples:
            >>> service = LeaseService()
            >>> active_leases = service.filter(contract_generated=True)
        """
        instances = list(self.get_queryset().filter(**kwargs))
        self.logger.debug(f"Filtered {len(instances)} {self.model.__name__} instances with {kwargs}")
        return instances
