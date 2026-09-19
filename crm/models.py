from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
from core.models import Brand, PhoneModel, RepairService

# ─── Branch (Филиал) ─────────────────────────────────────────────────────────

class Branch(models.Model):
    name = models.CharField("Название", max_length=200)
    address = models.CharField("Адрес", max_length=300, blank=True)
    phone = models.CharField("Телефон", max_length=30, blank=True)
    email = models.EmailField("Email", blank=True)
    is_active = models.BooleanField("Активен", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Филиал"
        verbose_name_plural = "Филиалы"
        ordering = ['name']

    def __str__(self):
        return self.name


# ─── User / Employee ─────────────────────────────────────────────────────────

class UserProfile(models.Model):
    ROLES = [
        ('admin', 'Администратор'),
        ('manager', 'Менеджер'),
        ('master', 'Мастер'),
        ('employee', 'Сотрудник'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField("Роль", max_length=20, choices=ROLES, default='employee')
    phone    = models.CharField("Телефон", max_length=30, blank=True)
    telegram = models.CharField("ВКонтакте", max_length=100, blank=True)
    notes    = models.TextField("Заметки (только для админа)", blank=True)
    branch   = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='active_employees', verbose_name="Активный филиал сегодня")
    branches = models.ManyToManyField(Branch, blank=True,
                                      related_name='staff_profiles', verbose_name="Доступные филиалы")
    photo    = models.ImageField("Фото", upload_to='employees/', blank=True, null=True)
    # Salary settings
    repair_percent = models.DecimalField("% с ремонтов", max_digits=5, decimal_places=2, default=Decimal('0'))
    accessory_percent = models.DecimalField("% с аксессуаров", max_digits=5, decimal_places=2, default=Decimal('0'))
    base_salary = models.DecimalField("Оклад", max_digits=10, decimal_places=2, default=Decimal('0'))
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        verbose_name = "Профиль сотрудника"
        verbose_name_plural = "Профили сотрудников"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def is_admin(self): return self.role == 'admin'
    @property
    def is_manager(self): return self.role in ('admin', 'manager')
    @property
    def is_master(self): return self.role == 'master'


# ─── Customer ────────────────────────────────────────────────────────────────

class Customer(models.Model):
    name = models.CharField("ФИО", max_length=200)
    phone = models.CharField("Телефон", max_length=30)
    email = models.EmailField("Email", blank=True)
    notes = models.TextField("Примечания", blank=True)
    telegram_id = models.CharField("VK ID", max_length=50, blank=True, db_index=True)
    pd_consent = models.BooleanField("Согласие на ПД", default=False)
    pd_consent_at = models.DateTimeField("Дата согласия на ПД", null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='customers', verbose_name="Филиал")
    created_at = models.DateTimeField("Дата добавления", auto_now_add=True)

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} | {self.phone}"

    @property
    def total_orders(self):
        return self.repairs.count()

    @property
    def total_spent(self):
        return self.repairs.filter(status='issued').aggregate(
            total=Sum('final_cost'))['total'] or Decimal('0')


# ─── Supplier ────────────────────────────────────────────────────────────────

class Supplier(models.Model):
    name = models.CharField("Название", max_length=200)
    contact_person = models.CharField("Контактное лицо", max_length=200, blank=True)
    phone = models.CharField("Телефон", max_length=30, blank=True)
    email = models.EmailField("Email", blank=True)
    website = models.URLField("Сайт", blank=True)
    address = models.CharField("Адрес", max_length=300, blank=True)
    notes = models.TextField("Примечания", blank=True)
    is_active = models.BooleanField("Активен", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Поставщик"
        verbose_name_plural = "Поставщики"
        ordering = ['name']

    def __str__(self):
        return self.name


# ─── Warehouse: Parts ────────────────────────────────────────────────────────

class Part(models.Model):
    name = models.CharField("Название", max_length=200)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Марка")
    phone_model = models.ForeignKey(PhoneModel, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Модель")
    sku = models.CharField("Артикул", max_length=100, blank=True)
    quantity = models.IntegerField("Количество", default=0)
    min_quantity = models.PositiveIntegerField("Мин. остаток", default=1)
    purchase_price = models.DecimalField("Закупочная цена", max_digits=10, decimal_places=2, default=0)
    sale_price = models.DecimalField("Цена продажи", max_digits=10, decimal_places=2, default=0)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Поставщик")
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Филиал")
    photo = models.ImageField("Фото", upload_to='parts/', blank=True, null=True)
    notes = models.TextField("Примечания", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Запчасть"
        verbose_name_plural = "Запчасти"
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return 0 < self.quantity <= self.min_quantity

    @property
    def is_out_of_stock(self):
        return self.quantity <= 0

    @property
    def stock_value(self):
        return self.purchase_price * self.quantity


# ─── Warehouse: Accessories ──────────────────────────────────────────────────

class Accessory(models.Model):
    CATEGORIES = [
        ('case', 'Чехлы'),
        ('glass', 'Стёкла / плёнки'),
        ('charger', 'Зарядки / кабели'),
        ('audio', 'Наушники'),
        ('other', 'Прочее'),
    ]
    name = models.CharField("Название", max_length=200)
    category = models.CharField("Категория", max_length=20, choices=CATEGORIES, default='other')
    sku = models.CharField("Артикул", max_length=100, blank=True)
    compatible_with = models.CharField("Совместимость", max_length=200, blank=True)
    quantity = models.IntegerField("Количество", default=0)
    min_quantity = models.PositiveIntegerField("Мин. остаток", default=2)
    purchase_price = models.DecimalField("Закупочная цена", max_digits=10, decimal_places=2, default=0)
    sale_price = models.DecimalField("Цена продажи", max_digits=10, decimal_places=2, default=0)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Поставщик")
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Филиал")
    photo = models.ImageField("Фото", upload_to='accessories/', blank=True, null=True)
    notes = models.TextField("Примечания", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Аксессуар"
        verbose_name_plural = "Аксессуары"
        ordering = ['category', 'name']

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return 0 < self.quantity <= self.min_quantity

    @property
    def is_out_of_stock(self):
        return self.quantity <= 0


# ─── Warehouse: Stock Movements ──────────────────────────────────────────────

class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('in', 'Поступление'),
        ('out', 'Списание (ручное)'),
        ('repair', 'Использовано в ремонте'),
        ('sale', 'Продажа'),
        ('transfer', 'Перемещение'),
        ('inventory', 'Инвентаризация'),
        ('return', 'Возврат'),
    ]
    part = models.ForeignKey(Part, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='movements', verbose_name="Запчасть")
    accessory = models.ForeignKey(Accessory, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='movements', verbose_name="Аксессуар")
    movement_type = models.CharField("Тип", max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField("Кол-во (+/-)")
    unit_price = models.DecimalField("Цена за ед.", max_digits=10, decimal_places=2, default=0)
    comment = models.TextField("Комментарий", blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Филиал")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Движение склада"
        verbose_name_plural = "История движений"
        ordering = ['-created_at']

    def __str__(self):
        item = self.part or self.accessory
        return f"{self.get_movement_type_display()} | {item} | {self.quantity:+d}"


# ─── Helper ───────────────────────────────────────────────────────────────────

def _next_number(model, prefix):
    year = timezone.now().year
    last = model.objects.filter(order_number__startswith=f'{prefix}-{year}-').order_by('-id').first()
    num = int(last.order_number.split('-')[-1]) + 1 if last else 1
    return f'{prefix}-{year}-{num:04d}'


# ─── Repair Orders ───────────────────────────────────────────────────────────

class RepairOrder(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('diagnosis', 'Диагностика'),
        ('waiting_parts', 'Ожидание запчастей'),
        ('in_progress', 'В работе'),
        ('approval', 'На согласовании'),
        ('done', 'Готов к выдаче'),
        ('issued', 'Выдан'),
        ('cancelled', 'Отменён'),
    ]
    STATUS_COLORS = {
        'new': 'gray',
        'diagnosis': 'orange',
        'waiting_parts': 'yellow',
        'in_progress': 'blue',
        'approval': 'purple',
        'done': 'green',
        'issued': 'teal',
        'cancelled': 'red',
    }
    STATUS_BG = {
        'new': 'bg-gray-500/20 text-gray-300 border-gray-500/30',
        'diagnosis': 'bg-orange-500/20 text-orange-300 border-orange-500/30',
        'waiting_parts': 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
        'in_progress': 'bg-blue-500/20 text-blue-300 border-blue-500/30',
        'approval': 'bg-purple-500/20 text-purple-300 border-purple-500/30',
        'done': 'bg-green-500/20 text-green-300 border-green-500/30',
        'issued': 'bg-teal-500/20 text-teal-300 border-teal-500/30',
        'cancelled': 'bg-red-500/20 text-red-300 border-red-500/30',
    }

    order_number = models.CharField("Номер заказа", max_length=20, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='repairs', verbose_name="Клиент")
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, verbose_name="Марка")
    phone_model = models.ForeignKey(PhoneModel, on_delete=models.PROTECT, verbose_name="Модель")
    imei = models.CharField("IMEI / S/N", max_length=50, blank=True)
    appearance = models.TextField("Внешний вид / комплектация", blank=True)
    device_password = models.CharField("Пароль устройства", max_length=100, blank=True)
    complaint = models.TextField("Жалоба клиента / неисправность", blank=True)
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='new')
    deadline = models.DateField("Срок выполнения", null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Филиал")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_repairs',
                                   verbose_name="Менеджер")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='assigned_repairs', verbose_name="Мастер")
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    estimated_cost = models.DecimalField("Предварительная стоимость", max_digits=10, decimal_places=2, default=0)
    final_cost = models.DecimalField("Итоговая стоимость", max_digits=10, decimal_places=2, default=0)
    cost_price = models.DecimalField("Себестоимость", max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField("Скидка ₽", max_digits=10, decimal_places=2, default=0)
    notes = models.TextField("Внутренние заметки", blank=True)
    warranty_days = models.PositiveIntegerField("Гарантия (дней)", default=90)
    is_paid = models.BooleanField("Оплачен", default=False)
    paid_at = models.DateTimeField("Дата оплаты", null=True, blank=True)

    class Meta:
        verbose_name = "Заказ на ремонт"
        verbose_name_plural = "Заказы на ремонт"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['assigned_to']),
        ]

    def __str__(self):
        return f"{self.order_number} | {self.customer.name} | {self.phone_model}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = _next_number(RepairOrder, 'R')
        super().save(*args, **kwargs)

    @property
    def status_badge(self):
        return self.STATUS_BG.get(self.status, 'bg-gray-500/20 text-gray-300')

    @property
    def profit(self):
        return self.final_cost - self.cost_price

    @property
    def is_overdue(self):
        if self.deadline and self.status not in ('issued', 'cancelled'):
            return timezone.now().date() > self.deadline
        return False

    def recalculate_final_cost(self):
        # Запчасти НЕ добавляют к итогу — их стоимость уже заложена в цену услуги.
        # Закупочная цена запчастей идёт в себестоимость для расчёта маржи и зарплаты.
        services_total    = sum(s.price for s in self.order_services.all())
        accessories_total = sum(a.price * a.quantity for a in self.order_accessories.all())
        parts_cost        = sum(p.part.purchase_price * p.quantity for p in self.order_parts.all())
        accessories_cost  = sum(a.accessory.purchase_price * a.quantity for a in self.order_accessories.all())
        self.final_cost  = services_total + accessories_total - self.discount
        self.cost_price  = parts_cost + accessories_cost
        self.save(update_fields=['final_cost', 'cost_price'])


# ─── Order History (Timeline) ────────────────────────────────────────────────

class OrderHistory(models.Model):
    EVENT_TYPES = [
        ('status_change', 'Изменение статуса'),
        ('service_added', 'Добавлена услуга'),
        ('service_removed', 'Удалена услуга'),
        ('part_added', 'Добавлена запчасть'),
        ('part_removed', 'Удалена запчасть'),
        ('accessory_added', 'Добавлен аксессуар'),
        ('accessory_removed', 'Удалён аксессуар'),
        ('master_assigned', 'Назначен мастер'),
        ('payment', 'Оплата'),
        ('comment', 'Комментарий'),
        ('created', 'Заказ создан'),
    ]
    order = models.ForeignKey(RepairOrder, on_delete=models.CASCADE, related_name='history')
    event_type = models.CharField("Событие", max_length=30, choices=EVENT_TYPES)
    description = models.TextField("Описание")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "История заказа"
        verbose_name_plural = "История заказов"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order.order_number} | {self.get_event_type_display()}"

# ─── Order Services & Parts ──────────────────────────────────────────────────

class RepairOrderService(models.Model):
    order = models.ForeignKey(RepairOrder, on_delete=models.CASCADE, related_name='order_services')
    service = models.ForeignKey(RepairService, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField("Название работы", max_length=200)
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Работа"
        verbose_name_plural = "Работы"

    def __str__(self):
        return f"{self.name} — {self.price}₽"


class RepairOrderPart(models.Model):
    order = models.ForeignKey(RepairOrder, on_delete=models.CASCADE, related_name='order_parts')
    part = models.ForeignKey(Part, on_delete=models.PROTECT, verbose_name="Запчасть")
    quantity = models.PositiveIntegerField("Количество", default=1)
    price = models.DecimalField("Цена за шт.", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Запчасть в заказе"
        verbose_name_plural = "Запчасти в заказе"

    def __str__(self):
        return f"{self.part.name} x{self.quantity}"

    @property
    def total(self):
        return self.price * self.quantity


# ─── Accessories in repair order ─────────────────────────────────────────────

class RepairOrderAccessory(models.Model):
    order = models.ForeignKey(RepairOrder, on_delete=models.CASCADE, related_name='order_accessories',
                              verbose_name="Заказ")
    accessory = models.ForeignKey('Accessory', on_delete=models.PROTECT, verbose_name="Аксессуар")
    quantity = models.PositiveIntegerField("Количество", default=1)
    price = models.DecimalField("Цена за шт.", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Аксессуар в заказе"
        verbose_name_plural = "Аксессуары в заказе"

    def __str__(self):
        return f"{self.accessory.name} x{self.quantity}"

    @property
    def total(self):
        return self.price * self.quantity

    @property
    def profit(self):
        return (self.price - self.accessory.purchase_price) * self.quantity


# ─── Finance: Payments ───────────────────────────────────────────────────────

class PaymentRecord(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'Наличные'),
        ('card', 'Карта'),
        ('transfer', 'Перевод'),
        ('mixed', 'Смешанная оплата'),
    ]
    PAYMENT_TYPES = [
        ('repair', 'Ремонт'),
        ('sale', 'Продажа'),
        ('income', 'Приход'),
        ('expense', 'Расход'),
        ('salary', 'Зарплата'),
    ]
    repair_order = models.ForeignKey('RepairOrder', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='payments', verbose_name="Заказ")
    sale_order = models.ForeignKey('SaleOrder', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='payments', verbose_name="Продажа")
    payment_type = models.CharField("Тип", max_length=20, choices=PAYMENT_TYPES, default='repair')
    method = models.CharField("Метод", max_length=20, choices=PAYMENT_METHODS, default='cash')
    amount = models.DecimalField("Сумма", max_digits=10, decimal_places=2)
    amount_cash = models.DecimalField("Наличные", max_digits=10, decimal_places=2, default=0)
    amount_card = models.DecimalField("Карта", max_digits=10, decimal_places=2, default=0)
    description = models.CharField("Описание", max_length=300, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Филиал")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"
        ordering = ['-created_at']
        indexes = [models.Index(fields=['created_at'])]

    def __str__(self):
        return f"{self.get_payment_type_display()} | {self.amount}₽ | {self.created_at.date()}"


# ─── Finance: Expenses ───────────────────────────────────────────────────────

class Expense(models.Model):
    CATEGORIES = [
        ('rent', 'Аренда'),
        ('salary', 'Зарплата'),
        ('parts', 'Закупка запчастей'),
        ('equipment', 'Оборудование'),
        ('marketing', 'Маркетинг'),
        ('utilities', 'Коммунальные'),
        ('other', 'Прочее'),
    ]
    category = models.CharField("Категория", max_length=30, choices=CATEGORIES, default='other')
    description = models.CharField("Описание", max_length=300)
    amount = models.DecimalField("Сумма", max_digits=10, decimal_places=2)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Филиал")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    date = models.DateField("Дата", default=timezone.now)

    class Meta:
        verbose_name = "Расход"
        verbose_name_plural = "Расходы"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_category_display()} | {self.amount}₽"


# ─── Payroll ─────────────────────────────────────────────────────────────────

def current_year():
    return timezone.localdate().year


def current_month():
    return timezone.localdate().month


class PayrollRecord(models.Model):
    RECORD_TYPES = [
        ('repair_bonus', 'Бонус за ремонт'),
        ('sale_bonus', 'Бонус за продажу'),
        ('base_salary', 'Оклад'),
        ('bonus', 'Премия'),
        ('penalty', 'Штраф'),
    ]
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payroll_records',
                                 verbose_name="Сотрудник")
    record_type = models.CharField("Тип", max_length=20, choices=RECORD_TYPES)
    amount = models.DecimalField("Сумма", max_digits=10, decimal_places=2)
    description = models.CharField("Описание", max_length=300, blank=True)
    repair_order = models.ForeignKey(RepairOrder, on_delete=models.SET_NULL, null=True, blank=True,
                                     verbose_name="Заказ")
    period_year = models.PositiveIntegerField("Год", default=current_year)
    period_month = models.PositiveIntegerField("Месяц", default=current_month)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_payroll')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Запись зарплаты"
        verbose_name_plural = "Зарплатные записи"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee.get_full_name()} | {self.get_record_type_display()} | {self.amount}₽"


# ─── Sales ───────────────────────────────────────────────────────────────────

class SaleOrder(models.Model):
    order_number = models.CharField("Номер", max_length=20, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='sales', verbose_name="Клиент")
    customer_name = models.CharField("Имя покупателя", max_length=200, blank=True)
    customer_phone = models.CharField("Телефон", max_length=30, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Филиал")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField("Итого", max_digits=10, decimal_places=2, default=0)
    cost_price = models.DecimalField("Себестоимость", max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField("Скидка ₽", max_digits=10, decimal_places=2, default=0)
    notes = models.TextField("Примечания", blank=True)
    is_finalized = models.BooleanField("Завершён", default=False)
    payment_method = models.CharField("Метод оплаты", max_length=20,
                                      choices=PaymentRecord.PAYMENT_METHODS, default='cash')

    class Meta:
        verbose_name = "Продажа"
        verbose_name_plural = "Продажи"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order_number} | {self.total}₽"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = _next_number(SaleOrder, 'S')
        super().save(*args, **kwargs)

    @property
    def profit(self):
        return self.total - self.cost_price

    def recalculate_total(self):
        self.total = sum(i.price * i.quantity for i in self.items.all()) - self.discount
        self.cost_price = sum(
            (i.accessory.purchase_price * i.quantity) for i in self.items.select_related('accessory').all()
        )
        self.save(update_fields=['total', 'cost_price'])


class SaleOrderItem(models.Model):
    order = models.ForeignKey(SaleOrder, on_delete=models.CASCADE, related_name='items')
    accessory = models.ForeignKey(Accessory, on_delete=models.PROTECT, verbose_name="Аксессуар")
    quantity = models.PositiveIntegerField("Кол-во", default=1)
    price = models.DecimalField("Цена за шт.", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Позиция продажи"
        verbose_name_plural = "Позиции продажи"

    @property
    def total(self):
        return self.price * self.quantity


# ─── Tasks ───────────────────────────────────────────────────────────────────

class Task(models.Model):
    PRIORITIES = [
        ('low', 'Низкий'),
        ('medium', 'Средний'),
        ('high', 'Высокий'),
        ('urgent', 'Срочно'),
    ]
    STATUS_CHOICES = [
        ('open', 'Открыта'),
        ('in_progress', 'В работе'),
        ('done', 'Выполнена'),
        ('cancelled', 'Отменена'),
    ]
    title = models.CharField("Задача", max_length=300)
    description = models.TextField("Описание", blank=True)
    priority = models.CharField("Приоритет", max_length=10, choices=PRIORITIES, default='medium')
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='open')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='tasks', verbose_name="Исполнитель")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_tasks')
    repair_order = models.ForeignKey(RepairOrder, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='tasks', verbose_name="Заказ")
    due_date = models.DateField("Срок", null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Филиал")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        ordering = ['-created_at']

    def __str__(self):
        return self.title


# ─── Notifications ───────────────────────────────────────────────────────────

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('order_new', 'Новый заказ'),
        ('order_ready', 'Заказ готов'),
        ('order_overdue', 'Заказ просрочен'),
        ('low_stock', 'Низкий остаток'),
        ('comment', 'Комментарий'),
        ('task', 'Задача'),
        ('payment', 'Оплата'),
        ('penalty', 'Штраф'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField("Тип", max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField("Заголовок", max_length=200)
    message = models.TextField("Сообщение", blank=True)
    link = models.CharField("Ссылка", max_length=300, blank=True)
    is_read = models.BooleanField("Прочитано", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} | {self.title}"


# ─── Appointment (Запись на ремонт) ──────────────────────────────────────────

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новая'),
        ('confirmed', 'Подтверждена'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
    ]
    SOURCE_CHOICES = [
        ('crm', 'CRM'),
        ('telegram', 'Telegram'),
        ('vk', 'ВКонтакте'),
        ('website', 'Сайт'),
    ]

    name = models.CharField("Имя клиента", max_length=200)
    phone = models.CharField("Телефон", max_length=30)
    device = models.CharField("Устройство", max_length=200, blank=True)
    problem = models.TextField("Описание проблемы", blank=True)
    preferred_date = models.DateField("Желаемая дата", null=True, blank=True)
    preferred_time = models.TimeField("Желаемое время", null=True, blank=True)
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='new')
    source = models.CharField("Источник", max_length=20, choices=SOURCE_CHOICES, default='crm')
    branch = models.ForeignKey('Branch', on_delete=models.SET_NULL, null=True, blank=True,
                               verbose_name="Филиал", related_name='appointments')
    telegram_chat_id = models.CharField("VK user ID", max_length=50, blank=True)
    notes = models.TextField("Примечания (внутренние)", blank=True)
    created_order = models.ForeignKey(
        'RepairOrder', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='from_appointment',
        verbose_name="Созданный заказ"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Запись"
        verbose_name_plural = "Записи"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} | {self.phone} | {self.get_status_display()}"

    @property
    def status_badge(self):
        return {
            'new': 'badge-new',
            'confirmed': 'badge-in_progress',
            'completed': 'badge-done',
            'cancelled': 'badge-cancelled',
        }.get(self.status, 'badge-new')
