import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import TemplateView, DetailView
from django.urls import reverse_lazy

from rdmo.core.imports import handle_uploaded_file, validate_xml
from rdmo.core.views import ModelPermissionMixin
from rdmo.core.utils import get_model_field_meta, render_to_format

from .imports import import_catalog
from .models import Catalog, Section, Subsection, Question
from .serializers.export import CatalogSerializer as ExportSerializer
from .renderers import XMLRenderer

log = logging.getLogger(__name__)


class CatalogsView(ModelPermissionMixin, TemplateView):
    template_name = 'questions/catalogs.html'
    permission_required = 'questions.view_catalog'


    def get_context_data(self, **kwargs):
        context = super(CatalogsView, self).get_context_data(**kwargs)
        context['export_formats'] = settings.EXPORT_FORMATS
        context['meta'] = {
            'Catalog': get_model_field_meta(Catalog),
            'Section': get_model_field_meta(Section),
            'Subsection': get_model_field_meta(Subsection),
            'Question': get_model_field_meta(Question),
        }
        return context


class CatalogExportView(ModelPermissionMixin, DetailView):
    model = Catalog
    context_object_name = 'catalog'
    permission_required = 'questions.view_catalog'

    def render_to_response(self, context, **response_kwargs):
        format = self.kwargs.get('format')
        if format == 'xml':
            serializer = ExportSerializer(context['catalog'])
            response = HttpResponse(XMLRenderer().render(serializer.data), content_type="application/xml")
            response['Content-Disposition'] = 'filename="%s.xml"' % context['catalog'].key
            return response
        else:
            return render_to_format(self.request, format, context['catalog'].title, 'questions/catalog_export.html', context)


class CatalogImportXMLView(ModelPermissionMixin, DetailView):
    permission_required = ('questions.add_catalog', 'questions.change_catalog', 'questions.delete_catalog')
    success_url = reverse_lazy('catalogs')
    parsing_error_template = 'core/import_parsing_error.html'
    confirm_page_template = 'questions/catalogs_confirmation_page.html'

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(self.success_url)

    def post(self, request, *args, **kwargs):
        log.info('Validating post request')

        # in case of receiving xml data
        try:
            savelist = json.loads(request.POST['tabledata'])
        except KeyError:
            pass
        else:
            log.info('Post seems to come from confirmation page')
            return self.trigger_import(request, savelist, do_save=True)

        # when receiving upload file
        try:
            request.FILES['uploaded_file']
        except KeyError:
            return HttpResponseRedirect(self.success_url)
        else:
            log.info('Post from file import dialog')
            request.session['tempfile'] = handle_uploaded_file(request.FILES['uploaded_file'])
            return self.trigger_import(request, savelist={})

    def trigger_import(self, request, savelist={}, do_save=False):
        log.info('Parsing file ' + request.session.get('tempfile'))
        roottag, xmltree = validate_xml(request.session.get('tempfile'))
        if roottag == 'catalog':
            savelist = import_catalog(xmltree, savelist=savelist, do_save=do_save)
            if do_save is False:
                return self.render_confirmation_page(request, savelist=savelist)
            else:
                return HttpResponseRedirect(self.success_url)
        else:
            log.info('Xml parsing error. Import failed.')
            return render(request, self.parsing_error_template, status=400)

    def render_confirmation_page(self, request, savelist, *args, **kwargs):
        return render(request, self.confirm_page_template, {
            'status': 200,
            'savelist': sorted(savelist.items()),
        })
