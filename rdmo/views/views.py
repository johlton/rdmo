import json
import logging


from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView, ListView
from django.urls import reverse_lazy

from rdmo.core.imports import handle_uploaded_file, validate_xml
from rdmo.core.views import ModelPermissionMixin
from rdmo.core.utils import get_model_field_meta, render_to_format

from .imports import import_views
from .models import View
from .serializers.export import ViewSerializer as ExportSerializer
from .renderers import XMLRenderer

log = logging.getLogger(__name__)


class ViewsView(ModelPermissionMixin, TemplateView):
    template_name = 'views/views.html'
    permission_required = 'views.view_view'

    def get_context_data(self, **kwargs):
        context = super(ViewsView, self).get_context_data(**kwargs)
        context['export_formats'] = settings.EXPORT_FORMATS
        context['meta'] = {
            'View': get_model_field_meta(View)
        }
        return context


class ViewsExportView(ModelPermissionMixin, ListView):
    model = View
    context_object_name = 'views'
    permission_required = 'views.view_view'

    def render_to_response(self, context, **response_kwargs):
        format = self.kwargs.get('format')
        if format == 'xml':
            serializer = ExportSerializer(context['views'], many=True)
            response = HttpResponse(XMLRenderer().render(serializer.data), content_type="application/xml")
            response['Content-Disposition'] = 'filename="views.xml"'
            return response
        else:
            return render_to_format(self.request, format, _('Views'), 'views/views_export.html', context)


class ViewsImportXMLView(ModelPermissionMixin, ListView):
    permission_required = ('views.add_view', 'views.change_view', 'views.delete_view')
    success_url = reverse_lazy('views')
    parsing_error_template = 'core/import_parsing_error.html'
    confirm_page_template = 'views/views_confirmation_page.html'

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
        if roottag == 'views':
            savelist = import_views(xmltree, savelist=savelist, do_save=do_save)
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
