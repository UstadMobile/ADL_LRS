# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url

urlpatterns = patterns('umapi.views',
    url(r'^$', 'root_view', name='root_view'),
    url(r'^forward/$', 'forward', name='forward'),
    url(r'^login/$', 'login', name='umapilogin')
)
