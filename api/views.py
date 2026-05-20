from datetime import date
from decimal import Decimal

from django.db.models import Sum, Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Account, FundTransfer
from budgets.models import MonthlyPlan, MonthlyPlanItem
from categories.models import Category
from transactions.models import Transaction

from .serializers import (
    AccountSerializer,
    FundTransferSerializer,
    CategorySerializer,
    MonthlyPlanItemSerializer,
    MonthlyPlanSerializer,
    MonthlyPlanSummarySerializer,
    QuickTransactionSerializer,
    TransactionSerializer,
)


class AccountViewSet(viewsets.ModelViewSet):
    """CRUD de contas do usuário autenticado."""
    serializer_class = AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user).order_by('name')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='transfer',
            serializer_class=FundTransferSerializer)
    def transfer(self, request):
        """Transfere saldo entre contas do usuário autenticado.

        Transferência não entra como receita/despesa; apenas debita a conta de
        origem, credita a conta de destino e grava auditoria em FundTransfer.
        """
        serializer = FundTransferSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        transfer = serializer.save()
        out = FundTransferSerializer(transfer, context={'request': request}).data
        return Response(out, status=status.HTTP_201_CREATED)


class CategoryViewSet(viewsets.ModelViewSet):
    """CRUD de categorias do usuário autenticado."""
    serializer_class = CategorySerializer

    def get_queryset(self):
        qs = Category.objects.filter(user=self.request.user, is_active=True)
        category_type = self.request.query_params.get('type')
        if category_type in ('INCOME', 'EXPENSE'):
            qs = qs.filter(category_type=category_type)
        return qs.order_by('category_type', 'name')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TransactionViewSet(viewsets.ModelViewSet):
    """CRUD de transações do usuário autenticado."""
    serializer_class = TransactionSerializer

    def get_queryset(self):
        qs = Transaction.objects.filter(user=self.request.user).select_related(
            'account', 'category'
        )
        params = self.request.query_params

        transaction_type = params.get('type')
        if transaction_type in ('INCOME', 'EXPENSE'):
            qs = qs.filter(transaction_type=transaction_type)

        year = params.get('year')
        month = params.get('month')
        if year:
            qs = qs.filter(transaction_date__year=int(year))
        if month:
            qs = qs.filter(transaction_date__month=int(month))

        account_id = params.get('account')
        if account_id:
            qs = qs.filter(account_id=account_id)

        category_id = params.get('category')
        if category_id:
            qs = qs.filter(category_id=category_id)

        status_param = (params.get('status') or '').upper()
        valid_statuses = {choice[0] for choice in Transaction.STATUS_CHOICES}
        if status_param in valid_statuses:
            qs = qs.filter(status=status_param)

        return qs.order_by('-transaction_date', '-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm(self, request, pk=None):
        """Efetiva manualmente uma transação pendente."""
        transaction_obj = self.get_object()
        if transaction_obj.status != 'PENDING':
            return Response(
                {'detail': 'Apenas transações pendentes podem ser efetivadas.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        transaction_obj.status = 'CONFIRMED'
        transaction_obj.auto_confirm = False
        transaction_obj.confirmed_at = timezone.now()
        transaction_obj.save()

        return Response(
            self.get_serializer(transaction_obj).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['get'], url_path='pending')
    def pending(self, request):
        """Relatório manual de transações pendentes a efetivar."""
        qs = self.get_queryset().filter(status='PENDING')

        due_raw = (request.query_params.get('due') or '').lower()
        due_only = due_raw in ('1', 'true', 'yes', 'sim')
        until_raw = (request.query_params.get('until') or '').strip()
        until_date = None

        if due_only:
            until_date = date.today()
        elif until_raw:
            until_date = parse_date(until_raw)
            if until_date is None:
                return Response(
                    {'detail': 'Parâmetro until inválido. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if until_date:
            qs = qs.filter(transaction_date__lte=until_date)

        totals = qs.aggregate(
            income=Sum('amount', filter=Q(transaction_type='INCOME')),
            expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
        )
        income = totals['income'] or Decimal('0.00')
        expenses = totals['expenses'] or Decimal('0.00')

        return Response({
            'as_of': date.today().isoformat(),
            'filters': {
                'due': due_only,
                'until': until_date.isoformat() if until_date else None,
                'type': request.query_params.get('type'),
                'account': request.query_params.get('account'),
                'category': request.query_params.get('category'),
            },
            'summary': {
                'count': qs.count(),
                'income': str(income),
                'expenses': str(expenses),
                'net': str(income - expenses),
            },
            'results': self.get_serializer(qs, many=True).data,
        })

    @action(detail=False, methods=['post'], url_path='quick',
            serializer_class=QuickTransactionSerializer)
    def quick(self, request):
        """Cria transação com payload mínimo (PWA / Hermes / Background Sync).

        Aceita: amount, transaction_type, account, category, [description,
        transaction_date, client_id]. Defaults: data=hoje,
        description=categoria.name. Idempotência por client_id (best-effort —
        descarta retransmissão se já existir transação com client_id idêntico
        nas últimas 24h gravado em notes).
        """
        from datetime import timedelta
        from django.utils import timezone

        client_id = (request.data.get('client_id') or '').strip()

        # Idempotência simples: client_id é gravado como prefixo em notes.
        # Migração futura criará campo dedicado + unique constraint.
        if client_id:
            tag = f'[client_id:{client_id}]'
            since = timezone.now() - timedelta(hours=24)
            existing = (
                Transaction.objects.filter(
                    user=request.user,
                    notes__contains=tag,
                    created_at__gte=since,
                )
                .order_by('-created_at')
                .first()
            )
            if existing:
                return Response(
                    QuickTransactionSerializer(existing, context={'request': request}).data,
                    status=status.HTTP_200_OK,
                )

        serializer = QuickTransactionSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        notes = ''
        if client_id:
            notes = f'[client_id:{client_id}]'

        instance = serializer.save(user=request.user, notes=notes)
        out = QuickTransactionSerializer(instance, context={'request': request}).data
        return Response(out, status=status.HTTP_201_CREATED)


class DashboardSnapshotView(APIView):
    """Snapshot consolidado para PWA/Hermes — uma chamada cobre o dashboard.

    Padrão (uso Hermes / chamada barata): saldo total, totais do mês,
    contagem de transações e top 5 transações recentes.

    Query param ``include=`` (CSV) adiciona pacotes opcionais:

      - ``budgets`` → top 5 orçamentos ativos (com percentage_used)
      - ``goals`` → top 3 metas ativas (com progress_pct)
      - ``chart_6m`` → 6 meses de receitas/despesas para o gráfico de
        linha do dashboard mobile

    Exemplo: ``/api/v1/dashboard/snapshot/?include=budgets,goals,chart_6m``

    Pensado para cache ``stale-while-revalidate`` no Service Worker.
    """

    def get(self, request):
        from datetime import date

        today = date.today()
        summary = Transaction.get_monthly_summary(
            request.user, today.year, today.month
        )

        total_balance = (
            Account.objects.filter(user=request.user, is_active=True)
            .aggregate(s=Sum('balance'))['s']
            or Decimal('0.00')
        )

        recent = (
            Transaction.objects.filter(user=request.user)
            .select_related('account', 'category')
            .order_by('-transaction_date', '-created_at')[:5]
        )

        income_month = summary['income']
        savings_pct = (
            int((summary['balance'] / income_month) * 100)
            if income_month and income_month > 0 else 0
        )

        payload = {
            'as_of': today.isoformat(),
            'totals': {
                'total_balance': str(total_balance),
                'income_month': str(summary['income']),
                'expenses_month': str(summary['expenses']),
                'balance_month': str(summary['balance']),
                'savings_pct': savings_pct,
                'transaction_count_month': summary['transaction_count'],
            },
            'recent_transactions': TransactionSerializer(
                recent, many=True, context={'request': request}
            ).data,
        }

        include_csv = (request.query_params.get('include') or '').lower()
        include = {p.strip() for p in include_csv.split(',') if p.strip()}

        if 'budgets' in include:
            payload['budgets'] = self._top_budgets(request.user, today)
        if 'goals' in include:
            payload['goals'] = self._top_goals(request.user)
        if 'chart_6m' in include:
            payload['chart_6m'] = self._chart_6m(request.user, today)

        return Response(payload)

    @staticmethod
    def _top_budgets(user, today):
        from budgets.models import Budget

        budgets = (
            Budget.objects.filter(
                user=user,
                is_active=True,
                start_date__lte=today,
                end_date__gte=today,
            )
            .select_related('category')[:5]
        )
        out = []
        for b in budgets:
            pct = float(b.percentage_used or 0)
            out.append({
                'id': b.id,
                'name': b.name,
                'planned_amount': str(b.planned_amount),
                'spent_amount': str(b.spent_amount),
                'percentage_used': round(pct, 1),
                'category': b.category.name if b.category_id else None,
                'status': (
                    'over' if pct >= 100
                    else 'critical' if pct >= 80
                    else 'warning' if pct >= 50
                    else 'ok'
                ),
            })
        return out

    @staticmethod
    def _top_goals(user):
        from goals.models import Goal

        goals = (
            Goal.objects.filter(user=user, status=Goal.STATUS_ACTIVE)
            .order_by('-current_amount')[:3]
        )
        return [
            {
                'id': g.id,
                'name': g.name,
                'icon': g.icon or '🎯',
                'color': g.color or '#0ea5e9',
                'current_amount': str(g.current_amount),
                'target_amount': str(g.target_amount),
                'progress_pct': float(g.progress_pct or 0),
                'deadline': g.deadline.isoformat() if g.deadline else None,
            }
            for g in goals
        ]

    @staticmethod
    def _chart_6m(user, today):
        """Receitas/despesas dos últimos 6 meses (inclusive o atual).

        Mesma agregação do ``DashboardView.get_context_data`` mas em formato
        que o cliente PWA possa renderizar sem rebuild.
        """
        from datetime import date as _date
        from django.db.models import Case, DecimalField, Value, When
        from django.db.models.functions import TruncMonth

        total_months_start = today.year * 12 + today.month - 6
        chart_start = _date(
            total_months_start // 12,
            (total_months_start % 12) + 1,
            1,
        )

        rows = (
            Transaction.objects
            .filter(user=user, transaction_date__gte=chart_start, status='CONFIRMED')
            .annotate(month=TruncMonth('transaction_date'))
            .values('month')
            .annotate(
                income=Sum(Case(
                    When(transaction_type='INCOME', then='amount'),
                    default=Value(Decimal('0')),
                    output_field=DecimalField(),
                )),
                expenses=Sum(Case(
                    When(transaction_type='EXPENSE', then='amount'),
                    default=Value(Decimal('0')),
                    output_field=DecimalField(),
                )),
            )
            .order_by('month')
        )
        by_ym = {(r['month'].year, r['month'].month): r for r in rows}

        month_names = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                       'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        labels, income, expenses = [], [], []
        for i in range(5, -1, -1):
            tm = today.year * 12 + today.month - 1 - i
            y, m = tm // 12, (tm % 12) + 1
            row = by_ym.get((y, m))
            labels.append(f'{month_names[m - 1]}/{str(y)[-2:]}')
            income.append(float(row['income']) if row else 0.0)
            expenses.append(float(row['expenses']) if row else 0.0)

        return {'labels': labels, 'income': income, 'expenses': expenses}


class SyncSinceView(APIView):
    """Endpoint de delta para o Service Worker — retorna o que mudou desde `ts`.

    Usado pelo SW para reconciliar caches locais quando o usuário volta online.
    Retorna registros criados/atualizados em accounts, categories e transactions.

    Query params:
      - ``ts`` (obrigatório): ISO 8601 (ex.: ``2026-05-12T08:00:00Z``).
        Usa-se ``parse_datetime`` do Django (aceita formato com/sem TZ).

    Resposta:
      ``{server_time, since, accounts, categories, transactions}``

    Notas de design:
      - Categorias só têm ``created_at`` (não há ``updated_at``), então o
        delta cobre criações apenas. Aceitável: categorias quase nunca
        editam após criadas.
      - Não há soft-delete no schema atual — exclusões não aparecem no
        delta. Quando introduzirmos soft-delete (M7), retornaremos
        ``deleted: {accounts: [ids], ...}`` aqui.
    """

    def get(self, request):
        from django.utils.dateparse import parse_datetime
        from django.utils import timezone as _tz

        ts_raw = request.query_params.get('ts', '').strip()
        if not ts_raw:
            return Response(
                {'detail': 'Parâmetro ?ts é obrigatório (ISO 8601).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ts = parse_datetime(ts_raw)
        if ts is None:
            return Response(
                {'detail': 'Formato de timestamp inválido (use ISO 8601).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if _tz.is_naive(ts):
            ts = _tz.make_aware(ts, _tz.get_current_timezone())

        accounts_qs = (
            Account.objects.filter(user=request.user, updated_at__gt=ts)
            .order_by('updated_at')
        )
        categories_qs = (
            Category.objects.filter(user=request.user, created_at__gt=ts)
            .order_by('created_at')
        )
        transactions_qs = (
            Transaction.objects.filter(user=request.user, updated_at__gt=ts)
            .select_related('account', 'category')
            .order_by('updated_at')
        )

        return Response({
            'server_time': _tz.now().isoformat(),
            'since': ts.isoformat(),
            'accounts': AccountSerializer(
                accounts_qs, many=True, context={'request': request}
            ).data,
            'categories': CategorySerializer(
                categories_qs, many=True, context={'request': request}
            ).data,
            'transactions': TransactionSerializer(
                transactions_qs, many=True, context={'request': request}
            ).data,
        })


class ReceiptDraftView(APIView):
    """Recebe imagem de comprovante e devolve um *draft* de transação.

    Aceita tanto JSON (cliente normal) quanto multipart/form-data — este
    último é o que o ``share_target`` do manifest envia quando o usuário
    compartilha uma imagem do app de Galeria/Câmera diretamente para o
    PWA.

    **Estado atual:** OCR via Google Vision **ainda não está integrado
    neste serviço** (a integração vive no agente Hermes). Esta view age
    como contrato estável: aceita o upload, valida o tipo MIME, persiste
    metadados básicos e devolve um draft *vazio* que o cliente preenche
    e confirma via ``POST /api/v1/transactions/quick/``.

    Quando integrarmos OCR aqui, basta substituir ``_extract_draft_from_image``
    pela chamada ao Vision sem mudar o contrato.

    Aceita campos do share_target: ``title``, ``text``, ``url`` (texto
    livre que pode ajudar o OCR a hintar categoria).

    Aceita arquivo em qualquer um dos campos: ``image``, ``receipt``,
    ``file``.
    """

    parser_classes = (MultiPartParser, FormParser, JSONParser)
    ACCEPTED_MIMES = ('image/png', 'image/jpeg', 'image/webp', 'application/pdf')
    MAX_FILE_SIZE = 8 * 1024 * 1024  # 8 MB

    def post(self, request):
        upload = (
            request.FILES.get('image')
            or request.FILES.get('receipt')
            or request.FILES.get('file')
        )
        if upload is None:
            return Response(
                {'detail': 'Envie um arquivo nos campos image, receipt ou file.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if upload.size > self.MAX_FILE_SIZE:
            return Response(
                {'detail': f'Arquivo excede {self.MAX_FILE_SIZE // (1024 * 1024)} MB.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content_type = (upload.content_type or '').lower()
        if content_type not in self.ACCEPTED_MIMES:
            return Response(
                {
                    'detail': 'Tipo de arquivo não suportado.',
                    'accepted': list(self.ACCEPTED_MIMES),
                    'received': content_type or 'desconhecido',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        title = (request.data.get('title') or '').strip()
        text_hint = (request.data.get('text') or '').strip()

        # Sugestão de conta = primeira ativa do usuário
        default_account = (
            Account.objects.filter(user=request.user, is_active=True)
            .order_by('id')
            .first()
        )

        draft = self._extract_draft_from_image(
            upload=upload,
            title_hint=title,
            text_hint=text_hint,
            user=request.user,
            default_account_id=default_account.id if default_account else None,
        )

        return Response(
            {
                'status': 'draft',
                'message': (
                    'Draft criado a partir do comprovante. Confirme os dados e '
                    'envie via POST /api/v1/transactions/quick/.'
                ),
                'draft': draft,
                'meta': {
                    'filename': upload.name,
                    'content_type': content_type,
                    'size': upload.size,
                    'ocr_engine': 'pending',  # placeholder até integrar Vision
                },
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @staticmethod
    def _extract_draft_from_image(*, upload, title_hint, text_hint, user, default_account_id):
        """Extrai um draft de transação a partir da imagem.

        **TODO(M7+):** integrar Google Cloud Vision aqui (ou delegar para o
        Hermes via fila). Hoje, retorna um draft vazio com hints textuais
        para o usuário completar manualmente — a UX é melhor que erro 501
        e mantém o ``share_target`` funcional desde o dia 1.
        """
        from datetime import date as _date

        description = title_hint or text_hint or 'Comprovante (preencha)'
        return {
            'transaction_type': 'EXPENSE',
            'amount': None,
            'description': description[:200],
            'transaction_date': _date.today().isoformat(),
            'account': default_account_id,
            'category': None,
            'confidence': {
                'amount': 0.0,
                'date': 0.0,
                'merchant': 0.0,
            },
        }


class MonthlySummaryView(APIView):
    """Resumo financeiro mensal: receitas, despesas, saldo e contagem."""

    def get(self, request):
        try:
            year = int(request.query_params.get('year', 0))
            month = int(request.query_params.get('month', 0))
        except (TypeError, ValueError):
            return Response(
                {'error': 'year e month devem ser inteiros.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (year and month):
            return Response(
                {'error': 'Parâmetros year e month são obrigatórios.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        summary = Transaction.get_monthly_summary(request.user, year, month)

        return Response({
            'year': year,
            'month': month,
            'income': str(summary['income']),
            'expenses': str(summary['expenses']),
            'balance': str(summary['balance']),
            'transaction_count': summary['transaction_count'],
        })


class YearlySummaryView(APIView):
    """Resumo financeiro anual: receitas e despesas por mês."""

    def get(self, request):
        try:
            year = int(request.query_params.get('year', 0))
        except (TypeError, ValueError):
            return Response(
                {'error': 'year deve ser inteiro.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not year:
            return Response(
                {'error': 'Parâmetro year é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        months = []
        for m in range(1, 13):
            s = Transaction.get_monthly_summary(request.user, year, m)
            months.append({
                'month': m,
                'income': str(s['income']),
                'expenses': str(s['expenses']),
                'balance': str(s['balance']),
                'transaction_count': s['transaction_count'],
            })

        totals = Transaction.objects.filter(
            user=request.user,
            transaction_date__year=year,
            status='CONFIRMED',
        ).aggregate(
            total_income=Sum('amount', filter=Q(transaction_type='INCOME')),
            total_expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
        )
        total_income = totals['total_income'] or Decimal('0.00')
        total_expenses = totals['total_expenses'] or Decimal('0.00')

        return Response({
            'year': year,
            'total_income': str(total_income),
            'total_expenses': str(total_expenses),
            'total_balance': str(total_income - total_expenses),
            'months': months,
        })


class MonthlyPlanViewSet(viewsets.ModelViewSet):
    serializer_class = MonthlyPlanSerializer

    def get_queryset(self):
        return MonthlyPlan.objects.filter(
            user=self.request.user
        ).order_by('-year', '-month')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        plan = self.get_object()
        if plan.status != MonthlyPlan.STATUS_DRAFT:
            return Response(
                {'detail': 'Apenas planos em rascunho podem ser ativados.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        MonthlyPlan.objects.filter(pk=plan.pk).update(status=MonthlyPlan.STATUS_ACTIVE)
        plan.refresh_from_db()
        return Response(self.get_serializer(plan).data)

    @action(detail=True, methods=['post'])
    def copy_from_previous(self, request, pk=None):
        plan = self.get_object()
        previous = (
            MonthlyPlan.objects.filter(user=request.user)
            .exclude(pk=plan.pk)
            .filter(
                Q(year__lt=plan.year)
                | Q(year=plan.year, month__lt=plan.month)
            )
            .order_by('-year', '-month')
            .first()
        )
        if not previous:
            return Response(
                {'detail': 'Nenhum plano anterior encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        copied = 0
        for item in previous.items.all():
            _, created = MonthlyPlanItem.objects.get_or_create(
                monthly_plan=plan,
                category=item.category,
                defaults={
                    'planned_amount': item.planned_amount,
                    'alert_threshold': item.alert_threshold,
                },
            )
            if created:
                copied += 1
        return Response({'copied_items': copied, 'plan': self.get_serializer(plan).data})

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        plan = self.get_object()
        return Response(
            MonthlyPlanSummarySerializer(plan, context={'request': request}).data
        )


class MonthlyPlanItemViewSet(viewsets.ModelViewSet):
    serializer_class = MonthlyPlanItemSerializer

    def get_queryset(self):
        qs = MonthlyPlanItem.objects.filter(
            monthly_plan__user=self.request.user
        ).select_related('category', 'monthly_plan')
        monthly_plan_id = self.request.query_params.get('monthly_plan')
        if monthly_plan_id:
            qs = qs.filter(monthly_plan_id=monthly_plan_id)
        return qs

    def perform_create(self, serializer):
        serializer.save()
