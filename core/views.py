from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Prefetch, Q
from django.utils.http import url_has_allowed_host_and_scheme
from .models import SiteSettings, Brand, PhoneModel, RepairService, Review, CallRequest
from crm.models import Appointment, Branch


LEGAL_DOCUMENTS = {
    'privacy': {
        'eyebrow': 'КОНФИДЕНЦИАЛЬНОСТЬ',
        'title': 'Политика конфиденциальности',
        'lead': 'Краткая информация о том, какие данные получает Kayros при обращении через сайт и зачем они нужны.',
        'sections': [
            ('Какие данные получает сервис', 'Имя, контакт для связи, модель устройства, описание неисправности и выбранный филиал — только то, что пользователь указывает в форме.'),
            ('Для чего они используются', 'Чтобы ответить на заявку, уточнить детали ремонта, согласовать визит и связаться по вопросу обслуживания устройства.'),
            ('Передача и защита', 'Данные не предназначены для открытой публикации. Доступ к ним должен предоставляться только сотрудникам, которым они нужны для обработки обращения.'),
            ('Обращение по данным', 'Для уточнения, исправления или удаления сведений свяжитесь с сервисом по телефону или другим контактом, указанным на странице «Контакты».'),
        ],
    },
    'personal-data': {
        'eyebrow': 'ПЕРСОНАЛЬНЫЕ ДАННЫЕ',
        'title': 'Согласие на обработку данных',
        'lead': 'Заглушка согласия для форм записи на ремонт и обратной связи.',
        'sections': [
            ('Состав согласия', 'Отправляя форму, пользователь разрешает Kayros обработать указанные имя, контакт, сведения об устройстве и текст обращения.'),
            ('Цель обработки', 'Регистрация заявки, обратная связь, предварительное уточнение работ и организация посещения сервисного центра.'),
            ('Действия с данными', 'Получение, систематизация, хранение, уточнение, использование для связи по заявке и удаление после достижения цели или получения законного требования.'),
            ('Отзыв согласия', 'Отозвать согласие можно обращением по контактам сервиса. До публикации окончательной редакции порядок и реквизиты оператора требуют юридической проверки.'),
        ],
    },
    'cookies': {
        'eyebrow': 'COOKIE И НАСТРОЙКИ',
        'title': 'Использование cookie',
        'lead': 'Сайт использует технические данные, необходимые для безопасной работы форм и сохранения выбранного оформления.',
        'sections': [
            ('Технические cookie', 'Django может устанавливать CSRF-cookie, чтобы защищать формы сайта от поддельных запросов. Он не используется для рекламного профилирования.'),
            ('Выбранная тема', 'Светлая или тёмная тема сохраняется в localStorage браузера под ключом kayros-theme. Эта настройка остаётся на устройстве пользователя.'),
            ('Аналитика', 'На текущем этапе отдельные рекламные и аналитические cookie на публичных страницах не заявлены. При подключении таких систем раздел нужно обновить.'),
            ('Управление', 'Cookie и локальные данные можно удалить в настройках браузера. После удаления сайт снова выберет тему на основании системных настроек.'),
        ],
    },
    'terms': {
        'eyebrow': 'УСЛОВИЯ СЕРВИСА',
        'title': 'Правила оказания услуг',
        'lead': 'Предварительная памятка о записи, диагностике, стоимости и гарантии.',
        'sections': [
            ('Запись и диагностика', 'Заявка на сайте подтверждает намерение связаться с сервисом. Состав работ определяется после осмотра и диагностики устройства.'),
            ('Стоимость и сроки', 'Цены и сроки на сайте являются ориентировочными. Итоговые условия зависят от модели, состояния устройства, сложности работ и выбранных комплектующих.'),
            ('Согласование работ', 'До начала дополнительных работ сервис должен сообщить их состав и стоимость клиенту. Конкретные условия фиксируются при приёме устройства.'),
            ('Гарантия', 'Условия и срок гарантии зависят от выполненной работы и комплектующих. Для текущих настроек сайта указан ориентир в 90 дней; окончательная редакция требует проверки документов компании.'),
        ],
    },
}


def home(request):
    reviews = Review.objects.filter(is_active=True)[:6]
    popular_services = RepairService.objects.filter(
        is_popular=True, is_active=True, phone_model__is_active=True,
        phone_model__brand__is_active=True,
    ).select_related('phone_model__brand')[:6]
    branches = Branch.objects.filter(is_active=True)
    brands = Brand.objects.filter(is_active=True, phone_models__is_active=True).distinct().prefetch_related(
        Prefetch('phone_models', queryset=PhoneModel.objects.filter(is_active=True))
    )
    return render(request, 'core/home.html', {
        'reviews': reviews,
        'popular_services': popular_services,
        'branches': branches,
        'brands': brands,
    })


def about(request):
    return render(request, 'core/about.html')


def prices(request):
    brands = Brand.objects.filter(is_active=True).prefetch_related('phone_models__services')
    search_q = request.GET.get('q', '').strip()
    selected_model = request.GET.get('model', '')
    
    result = []
    for brand in brands:
        brand_models = []
        for model in brand.phone_models.filter(is_active=True):
            services = model.services.filter(is_active=True)
            if search_q:
                model_or_brand_matches = (
                    search_q.lower() in model.name.lower()
                    or search_q.lower() in brand.name.lower()
                )
                if not model_or_brand_matches:
                    services = services.filter(name__icontains=search_q)
                if not services.exists():
                    continue
            if selected_model and str(model.id) != selected_model:
                continue
            if services.exists() or not search_q:
                brand_models.append({'model': model, 'services': list(services)})
        if brand_models:
            result.append({'brand': brand, 'models': brand_models})
    
    all_models = PhoneModel.objects.filter(
        is_active=True, brand__is_active=True,
    ).select_related('brand').order_by('brand__order','order','name')
    return render(request, 'core/prices.html', {
        'result': result, 'search_q': search_q,
        'selected_model': selected_model, 'all_models': all_models,
    })


def contacts(request):
    branches = Branch.objects.filter(is_active=True)
    return render(request, 'core/contacts.html', {'branches': branches})


def legal_page(request, document):
    return render(request, 'core/legal.html', {
        'document': LEGAL_DOCUMENTS[document],
        'document_key': document,
    })


def contact_request(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        device = request.POST.get('device', '').strip()
        problem = request.POST.get('message', '').strip()
        branch_id = request.POST.get('branch_id') or None
        pd_consent = request.POST.get('pd_consent')
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        field_limits = {
            'name': Appointment._meta.get_field('name').max_length,
            'phone': Appointment._meta.get_field('phone').max_length,
            'device': Appointment._meta.get_field('device').max_length,
        }
        error = None
        if not name or not phone:
            error = 'Укажите имя и телефон или ВКонтакте.'
        elif len(name) > field_limits['name']:
            error = 'Имя слишком длинное.'
        elif len(phone) > field_limits['phone']:
            error = 'Контакт слишком длинный.'
        elif len(device) > field_limits['device']:
            error = 'Название устройства слишком длинное.'
        elif len(problem) > 5000:
            error = 'Описание проблемы слишком длинное.'
        elif pd_consent not in {'on', 'true', '1'}:
            error = 'Подтвердите согласие на обработку персональных данных.'

        if not error:
            branch = None
            if branch_id:
                try:
                    branch = Branch.objects.filter(pk=int(branch_id), is_active=True).first()
                except (TypeError, ValueError):
                    branch = None
                if branch is None:
                    error = 'Выбранный филиал недоступен. Выберите другой или оставьте поле пустым.'
        if not error:
            Appointment.objects.create(
                name=name,
                phone=phone,
                device=device,
                problem=problem,
                source='website',
                branch=branch,
            )
            if is_ajax:
                return JsonResponse({'ok': True})
            messages.success(request, 'Запись принята! Мы свяжемся с вами в ближайшее время.')
        else:
            if is_ajax:
                return JsonResponse({'ok': False, 'error': error}, status=400)
            messages.error(request, error)

    referer = request.META.get('HTTP_REFERER', '')
    if referer and url_has_allowed_host_and_scheme(
        referer, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        return redirect(referer)
    return redirect('home')
