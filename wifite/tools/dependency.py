#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

class Dependency(object):
    required_attr_names = ['dependency_name', 'dependency_url', 'dependency_required']

    # https://stackoverflow.com/a/49024227
    def __init_subclass__(cls):
        for attr_name in cls.required_attr_names:
            if not attr_name in cls.__dict__:
                raise NotImplementedError(
                    "Attribute '{}' has not been overriden in class '{}'" \
                    .format(attr_name, cls.__name__)
                )


    @classmethod
    def fails_dependency_check(cls):
        from ..util.color import Color
        from ..util.process import Process

        if Process.exists(cls.dependency_name):
            return False

        if cls.dependency_required:
            Color.pl('{!} {R}error: required app {O}%s{R} was not found' % cls.dependency_name)
            Color.pl('     {W}install @ {C}%s{W}' % cls.dependency_url)
            return True

        else:
            Color.pl('{!} {O}warning: recommended app {R}%s{O} was not found' % cls.dependency_name)
            Color.pl('     {W}install @ {C}%s{W}' % cls.dependency_url)
            return False
