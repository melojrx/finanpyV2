# Tags para Transações — Design Spec

## Resumo

Adicionar sistema de tags (etiquetas) às transações financeiras, permitindo ao usuário carimbar lançamentos com marcadores livres para filtros e relatórios cruzados (tag + categoria + período). Modelo inspirado no Mobills.

## Decisões de Design

| Decisão | Escolha |
|---------|---------|
| Relação com Category | Ortogonal — tag é dimensão extra, não substitui categoria |
| Escopo | User-scoped, sem seed inicial |
| Gerenciamento | Tela dedicada CRUD + criação inline no form de transação |
| Atributos visuais | Minimalista (só nome). Cor gerada client-side via hash |
| API REST | CRUD completo em /api/v1/tags/ + campo em TransactionSerializer |
| Arquitetura | App Django dedicado `tags/` |

## Data Model

### Tag (tags/models.py)

```python
class Tag(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=50, verbose_name='Nome')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criada em')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'], name='unique_tag_per_user')
        ]
        ordering = ['name']
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'
        indexes = [
            models.Index(fields=['user', 'name']),
        ]

    def clean(self):
        self.name = self.name.strip().lower()
        if not self.name:
            raise ValidationError({'name': 'Tag name cannot be empty.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
```

### Relação ManyToMany (transactions/models.py)

```python
tags = models.ManyToManyField('tags.Tag', blank=True, related_name='transactions')
```

- Sem through table customizada
- `blank=True` — tags opcionais
- Sem impacto em signals existentes (M2M não dispara post_save)

## Views & URLs

### App tags/

| View | Tipo | URL | Função |
|------|------|-----|--------|
| TagListView | ListView | /tags/ | Lista paginada com chips |
| TagCreateView | CreateView | /tags/create/ | Form simples (nome) |
| TagUpdateView | UpdateView | /tags/<pk>/edit/ | Renomear |
| TagDeleteView | DeleteView | /tags/<pk>/delete/ | Confirmação + delete |

Todas com LoginRequiredMixin + queryset filtrado por request.user.

### Integração no form de transação

- Campo `tags` em TransactionForm como ModelMultipleChoiceField
- Widget: input text com autocomplete + chips renderizados
- Criação inline: texto novo → cria Tag no form.save()
- Tags salvas via `transaction.tags.set(tag_list)`

## Filtros

### TransactionFilterForm

- Novo campo `tags` (opcional, multi-select)
- Lógica: `queryset.filter(tags__in=selected_tags).distinct()`

### API query param

- `?tag=viagem,reembolso` → filtra transações com qualquer das tags listadas

## API REST

### TagViewSet

- Endpoint: `/api/v1/tags/`
- Operações: list, create, retrieve, update, destroy
- User-scoped via get_queryset + perform_create

### TransactionSerializer

- Leitura: `tags` como TagSerializer(many=True, read_only=True)
- Escrita: `tag_ids` como PrimaryKeyRelatedField(many=True, write_only=True, source='tags')

## Templates

| Arquivo | Função |
|---------|--------|
| templates/tags/tag_list.html | Lista com chips, ações |
| templates/tags/tag_form.html | Form criar/editar |
| templates/tags/tag_confirm_delete.html | Confirmação delete |
| templates/components/_tag_input.html | Widget autocomplete reutilizável |

## Testes

### tags/tests.py

- **Model:** criação, unicidade por user, normalização lowercase, validação vazio, isolamento entre users
- **Views:** CRUD completo, user-scoping, redirect correto, messages
- **Integração:** transação com tags, filtro por tag na listagem
- **API:** CRUD tag, transação com tag_ids, filtro ?tag=

## Não-escopo

- Cor/ícone customizável (futuro se necessário)
- Tags em budgets/goals (futuro)
- Merge de tags duplicadas
- Import/export de tags
- Limites de quantidade de tags por transação

## Impacto em código existente

- `transactions/models.py` — adicionar campo M2M
- `transactions/forms.py` — adicionar campo tags no TransactionForm e TransactionFilterForm
- `transactions/views.py` — passar tags no context, processar filtro
- `api/views.py` — registrar TagViewSet, adicionar filtro por tag
- `api/serializers.py` — TagSerializer + campo em TransactionSerializer
- `core/urls.py` — incluir tags.urls
- `settings.py` — adicionar 'tags' em INSTALLED_APPS
- Templates de transação — renderizar chips de tags
