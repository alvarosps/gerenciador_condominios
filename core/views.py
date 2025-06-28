# core/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.template.loader import render_to_string
from django.conf import settings
import os
import sys
import asyncio
from pyppeteer import launch
from datetime import date, timedelta
from jinja2 import Environment, FileSystemLoader

from .models import Building, Furniture, Apartment, Tenant, Lease
from .serializers import (BuildingSerializer, FurnitureSerializer, ApartmentSerializer,
                          TenantSerializer, LeaseSerializer)
from .contract_rules import regras_condominio
from .utils import format_currency, number_to_words

os.environ["PYPPETEER_NO_SIGNALS"] = "1"
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ViewSets básicos
class BuildingViewSet(viewsets.ModelViewSet):
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer

class FurnitureViewSet(viewsets.ModelViewSet):
    queryset = Furniture.objects.all()
    serializer_class = FurnitureSerializer

class ApartmentViewSet(viewsets.ModelViewSet):
    queryset = Apartment.objects.all()
    serializer_class = ApartmentSerializer

class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer

class LeaseViewSet(viewsets.ModelViewSet):
    queryset = Lease.objects.all()
    serializer_class = LeaseSerializer

    # Endpoint para gerar contrato em PDF
    @action(detail=True, methods=['post'])
    def generate_contract(self, request, pk=None):
        lease = self.get_object()
        
        # Para a geração do PDF, montamos o contexto para o template. A lógica abaixo espelha
        # a funcionalidade já existente, adaptada à estrutura dos modelos
        try:
            # Calcular data final com base na validade
            start_date = lease.start_date
            validity = lease.validity_months
            next_month_date = (start_date + timedelta(days=30)).strftime("%d/%m/%Y")
            final_date = (start_date + timedelta(days=validity*30)).strftime("%d/%m/%Y")
            
            # Cálculo do valor total: aluguel + limpeza + valor da caução da tag
            valor_tags = 50 if len(lease.tenants.all()) == 1 else 80
            valor_total = lease.rental_value + lease.cleaning_fee + valor_tags
            
            # Calcular os móveis que estão no apartamento, removendo os móveis do inquilino responsável
            apt_furniture = set(lease.apartment.furnitures.all())
            tenant_furniture = set(lease.responsible_tenant.furnitures.all())
            lease_furnitures = list(apt_furniture - tenant_furniture)
            
            context = {
                'tenant': lease.responsible_tenant,
                'building_number': lease.apartment.building.street_number,
                'apartment_number': lease.apartment.number,
                'furnitures': lease_furnitures,
                'validity': validity,
                'start_date': start_date.strftime("%d/%m/%Y"),
                'final_date': final_date,
                'rental_value': lease.rental_value,
                'next_month_date': next_month_date,
                'tag_fee': lease.tag_fee,
                'cleaning_fee': lease.cleaning_fee,
                'valor_total': valor_total,
                'rules': regras_condominio,
                'lease': lease,
                'valor_tags': valor_tags,
            }

            template_path = os.path.join(settings.BASE_DIR, 'core', 'templates')
            env = Environment(loader=FileSystemLoader(template_path))
            env.filters['currency'] = format_currency
            env.filters['extenso'] = number_to_words
            
            template = env.get_template('contract_template.html')
            html_content = template.render(context)
            
            # Caminhos para salvar PDF temporário e final
            base_dir = settings.BASE_DIR
            contracts_dir = os.path.join(base_dir, 'contracts', str(lease.apartment.building.street_number))
            os.makedirs(contracts_dir, exist_ok=True)
            pdf_path = os.path.join(contracts_dir, f"contract_apto_{lease.apartment.number}_{lease.id}.pdf")
            
            # Função assíncrona para gerar PDF usando pyppeteer
            async def create_pdf():
                browser = await launch(
                    handleSIGINT=False,
                    handleSIGTERM=False,
                    handleSIGHUP=False,
                    options={
                        'pipe': 'true',
                        'executablePath': "C:\Program Files\Google\Chrome\Application\chrome.exe",
                        'headless': True,
                        'args': [
                            '--headless',
                            '--full-memory-crash-report',
                            '--unlimited-storage',
                            '--no-sandbox',
                            '--disable-setuid-sandbox',
                            '--disable-dev-shm-usage',
                            '--disable-accelerated-2d-canvas',
                            '--no-first-run',
                            '--no-zygote',
                            '--disable-gpu',
                        ],
                    },
                )
                page = await browser.newPage()
                # Salvar arquivo HTML temporariamente
                temp_html_path = os.path.join(contracts_dir, f"temp_contract_{lease.id}.html")
                with open(temp_html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                file_url = f'file:///{temp_html_path}'
                await page.goto(file_url, {'waitUntil': 'networkidle2'})
                await page.pdf({'path': pdf_path, 'format': 'A4'})
                await browser.close()
                # Remover arquivo HTML temporário
                os.remove(temp_html_path)
            # loop = asyncio.new_event_loop()
            # asyncio.set_event_loop(loop)
            # loop.run_until_complete(create_pdf())
            # loop.close()
            asyncio.run(create_pdf())

            # Atualizar o status do contrato
            lease.contract_generated = True
            lease.save()
            
            return Response({"message": "Contrato gerado com sucesso!", "pdf_path": pdf_path}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Endpoint para cálculo de multa de atraso
    @action(detail=True, methods=['get'])
    def calculate_late_fee(self, request, pk=None):
        lease = self.get_object()
        today = date.today()
        # Supondo que o pagamento seja mensal; comparar o dia de vencimento com a data atual
        due_day = lease.due_day
        # Se o pagamento está atrasado
        if today.day > due_day:
            atraso_dias = today.day - due_day
            daily_rate = lease.rental_value / 30  # valor por dia
            multa = daily_rate * atraso_dias * 0.05  # 5% ao dia
            return Response({"late_days": atraso_dias, "late_fee": multa}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Aluguel não está atrasado."}, status=status.HTTP_200_OK)

    # Endpoint para alteração do dia de vencimento com cálculo da taxa
    @action(detail=True, methods=['post'])
    def change_due_date(self, request, pk=None):
        lease = self.get_object()
        new_due_day = request.data.get('new_due_day')
        if not new_due_day:
            return Response({"error": "Campo new_due_day é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            new_due_day = int(new_due_day)
            current_due_day = lease.due_day
            # Sempre considerando 30 dias no mês
            diff_days = abs(new_due_day - current_due_day)
            daily_rate = lease.rental_value / 30
            fee = daily_rate * diff_days
            # Atualiza o dia de vencimento
            lease.due_day = new_due_day
            lease.save()
            return Response({"message": "Dia de vencimento alterado.", "fee": fee}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
