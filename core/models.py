from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class Building(models.Model):
    street_number = models.PositiveIntegerField(unique=True, help_text="Número da rua (ex.: 836 ou 850)")
    name = models.CharField(max_length=100, help_text="Nome do prédio")
    address = models.CharField(max_length=200, help_text="Endereço completo do prédio")

    def __str__(self):
        return f"{self.name} - {self.street_number}"

class Furniture(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Nome do móvel (ex.: Fogão, Geladeira, etc.)")
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
    
class Apartment(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='apartments')
    number = models.PositiveIntegerField(help_text="Número único do apartamento no prédio")
    interfone_configured = models.BooleanField(default=False, help_text="Indica se o interfone está configurado")
    contract_generated = models.BooleanField(default=False, help_text="Contrato foi gerado?")
    contract_signed = models.BooleanField(default=False, help_text="Contrato foi assinado?")
    
    rental_value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))], help_text="Valor do aluguel")
    cleaning_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Taxa de limpeza")
    max_tenants = models.PositiveIntegerField(help_text="Número máximo de inquilinos permitidos")
    
    is_rented = models.BooleanField(default=False, help_text="Apartamento alugado ou não")
    lease_date = models.DateField(blank=True, null=True, help_text="Data da locação (caso alugado)")
    last_rent_increase_date = models.DateField(blank=True, null=True, help_text="Data do último reajuste do aluguel")
    
    # Relação com móveis disponíveis no apartamento
    furnitures = models.ManyToManyField(Furniture, blank=True, related_name='apartments', help_text="Móveis presentes no apartamento")

    class Meta:
        unique_together = ('building', 'number')
        ordering = ['building__street_number', 'number']

    def __str__(self):
        return f"Apto {self.number} - {self.building.street_number}"

class Tenant(models.Model):
    # Dados básicos
    name = models.CharField(max_length=150, help_text="Nome completo ou razão social")
    cpf_cnpj = models.CharField(max_length=20, unique=True, help_text="CPF (ou CNPJ em caso de empresa)")
    is_company = models.BooleanField(default=False, help_text="Indica se é Pessoa Jurídica")
    rg = models.CharField(max_length=20, blank=True, null=True, help_text="RG (não obrigatório para empresas)")
    phone = models.CharField(max_length=20, help_text="Telefone de contato")
    marital_status = models.CharField(max_length=50, help_text="Estado civil")
    profession = models.CharField(max_length=100, help_text="Profissão")

    # Dados financeiros e administrativos
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Valor da caução, se houver")
    cleaning_fee_paid = models.BooleanField(default=False, help_text="Indica se pagou a taxa de limpeza")
    tag_deposit_paid = models.BooleanField(default=False, help_text="Indica se o caução das tags já foi pago")
    rent_due_day = models.PositiveIntegerField(help_text="Dia do vencimento do aluguel", default=1)
    
    # Relação com móveis próprios do inquilino
    furnitures = models.ManyToManyField(Furniture, blank=True, related_name='tenants', help_text="Móveis próprios do inquilino")

    def __str__(self):
        return self.name
    
class Dependent(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='dependents')
    name = models.CharField(max_length=150, help_text="Nome do dependente")
    phone = models.CharField(max_length=20, help_text="Telefone do dependente")

    def __str__(self):
        return f"{self.name} (dependente de {self.tenant.name})"

class Lease(models.Model):
    apartment = models.OneToOneField(Apartment, on_delete=models.CASCADE, related_name='lease')
    responsible_tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name='leases_responsible', help_text="Inquilino responsável pela locação")
    tenants = models.ManyToManyField(Tenant, related_name='leases', help_text="Inquilinos que residem no apartamento")
    number_of_tenants = models.PositiveIntegerField(help_text="Número de inquilinos no contrato", default=1)

    start_date = models.DateField(help_text="Data de início da locação")
    validity_months = models.PositiveIntegerField(help_text="Validade do contrato em meses")
    due_day = models.PositiveIntegerField(help_text="Dia do vencimento do aluguel")
    
    rental_value = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor do aluguel")
    cleaning_fee = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor da taxa de limpeza")
    tag_fee = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor da caução da tag", default=0)
    
    contract_generated = models.BooleanField(default=False, help_text="Indica se o contrato foi gerado")
    contract_signed = models.BooleanField(default=False, help_text="Indica se o contrato foi assinado")
    interfone_configured = models.BooleanField(default=False, help_text="Indica se o interfone foi configurado")
    
    warning_count = models.PositiveIntegerField(default=0, help_text="Número de avisos do inquilino por descumprimento das regras")

    def __str__(self):
        return f"Locação do Apto {self.apartment.number} - {self.apartment.building.street_number}"