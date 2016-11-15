import hashlib
import thread

__all__ = ['ValidationException', 'ValidationWarningException', 'MinLengthException', 'MaxLengthException']


class ValidationException(ValueError):
    WARNING_LEVEL_USER = 0
    WARNING_LEVEL_INTERNAL = 1

    def __init__(self, *args, **kwargs):
        self.error_dict = kwargs.pop('error_dict', None)
        self.field = kwargs.pop('field', 'unknown') or 'unknown'
        self.table = kwargs.pop('table', 'unknown') or 'unknown'
        self.form_name = kwargs.pop('form_name', None)
        self.warning_level = kwargs.pop('warning_level', None)
        self.warning_key = kwargs.pop('warning_key', None)
        self.warning_ignored = False
        ValueError.__init__(self, *args, **kwargs)

    def __unicode__(self):
        if self.error_dict is not None:
            return u', '.join([u'{}.{}: {}'.format(y.table, x, y) for x, y in self.error_dict.items()])
        return ValueError.__unicode__(self)

    @classmethod
    def create_warning(cls, warning_level, name, value, *args, **kwargs):
        kwargs['warning_level'] = warning_level

        kwargs['warning_key'] = hashlib.sha1(('%s-%s-%s-%s' % (warning_level, name, value, args[0])).encode('utf-8')).hexdigest()
        return ValidationException(*args, **kwargs)

    @staticmethod
    def merge_errors(errors, e, prefix=None):
        if not e:
            return errors

        prefix = prefix or ''
        if isinstance(e, dict):
            for k, v in e.items():
                v.field = k
                errors[prefix + k] = v
        elif e.error_dict:
            for k, v in e.error_dict.items():
                v.field = k
                errors[prefix + k] = v
        else:
            errors[prefix + e.field] = e
        return errors

    @classmethod
    def handle_warnings(cls, errors, values):
        return {k: v for (k, v) in [(k, v.handle_warning(values)) for (k, v) in errors.items()] if not hasattr(v, 'warning_ignored') or not v.warning_ignored}

    def handle_warning(self, values):
        self.warning_ignored = 'om_ignore' in values and values['om_ignore'].get(self.warning_key, False)
        return self

    def rest_as_json(self, api_user, user, top_level_is_list=False, top_level_obj=None):
        return unicode(self)


class ValidationWarningException(ValidationException):
    overrides = {}

    @classmethod
    def register_overrides(cls, keys):
        tid = thread.get_ident()
        if tid not in cls.overrides:
            cls.overrides[tid] = {}

        for k in keys:
            cls.overrides[tid][k] = True

    @classmethod
    def has_override(cls, key):
        pass


class MinLengthException(ValidationException):
    pass


class MaxLengthException(ValidationException):
    pass
