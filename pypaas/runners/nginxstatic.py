#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import os.path
import shutil
import subprocess
import sys

from .. import util
from .base import BaseRunner


nginx_ssl_config = """
server {{
    listen 80 {extra_listen_options};
    listen [::]:80 {extra_listen_options};
    server_name {domain};
    rewrite ^ https://$http_host$request_uri? permanent;
}}
server {{
    listen 443 ssl {extra_listen_options};
    listen [::]:443 ssl {extra_listen_options};
    server_name {domain};
    ssl_certificate /etc/ssl/private/httpd/{domain}/{domain}.crt;
    ssl_certificate_key /etc/ssl/private/httpd/{domain}/{domain}.key;
    ssl_session_timeout 5m;
    ssl_dhparam /etc/ssl/private/httpd/dhparam.pem;
    ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
    ssl_ciphers 'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:kEDH+AESGCM:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA256:DHE-RSA-AES256-SHA256:DHE-DSS-AES256-SHA:DHE-RSA-AES256-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:AES:CAMELLIA:DES-CBC3-SHA:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!aECDH:!EDH-DSS-DES-CBC3-SHA:!EDH-RSA-DES-CBC3-SHA:!KRB5-DES-CBC3-SHA';
    ssl_prefer_server_ciphers on;
    add_header Strict-Transport-Security max-age=15768000;
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/ssl/private/httpd/{domain}/trusted_chain.crt;
    resolver 8.8.8.8 8.8.4.4;
    location / {{
        alias {path};
    }}
}}
"""  # nopep8 (silence pep8 warning about long lines)

nginx_config = """
server {{
    listen 80 {extra_listen_options};
    listen [::]:80 {extra_listen_options};
    server_name {domain};
    location / {{
        alias {path};
    }}
}}
"""  # nopep8 (silence pep8 warning about long lines)


class NginxStatic(BaseRunner):
    config_key = 'run_nginxstatic'

    @property
    def nginx_config_path(self):
        return os.path.expanduser(os.path.join(
            '~/nginx.d/', self.config['domain'] + '.conf'
        ))

    def configure(self):
        pass

    def start(self):
        util.mkdir_p(os.path.expanduser('~/nginx.d/'))
        try:
            # Remove old broken config
            os.unlink(self.nginx_config_path + '.broken')
        except FileNotFoundError:
            pass

        subdirectory = self.config.get('subdirectory', '')
        while subdirectory.startswith("/"):
            subdirectory = subdirectory[1:]
        args = dict(
            domain=self.config['domain'],
            extra_listen_options=self.config.get(
                'extra_listen_options', ''
            ),
            path=os.path.join(
                self.app.current_checkout.path,
                subdirectory
            )
        )
        if self.config.get('ssl', True):
            util.replace_file(
                self.nginx_config_path,
                nginx_ssl_config.format(**args)
            )
        else:
            util.replace_file(
                self.nginx_config_path,
                nginx_config.format(**args)
            )
        try:
            subprocess.check_call(['sudo', '/usr/sbin/nginx', '-t'])
        except subprocess.CalledProcessError:
            # That file is probably broken => rename it
            os.rename(
                self.nginx_config_path,
                self.nginx_config_path + '.broken'
            )
            raise RuntimeError('nginx configuration failed')

        subprocess.check_call(['sudo', '/usr/sbin/nginx', '-s', 'reload'])

    def stop(self):
        try:
            os.unlink(self.nginx_config_path)
            subprocess.check_call(['sudo', '/usr/sbin/nginx', '-s', 'reload'])
        except FileNotFoundError:
            pass
