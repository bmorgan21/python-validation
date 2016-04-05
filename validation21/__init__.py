import decimal
import re
import inspect

from datetime import datetime, date, time
from dateutil.parser import parse

import enum21 as enum

from exception import *


def split_thousands(s, t_sep=',', d_sep='.'):
    '''Splits a general float on thousands. GIGO on general input'''
    if s is None:
        return 0

    if not isinstance(s, str):
        s = str(s)

    cnt = 0
    num_chars = d_sep + '0123456789'
    ls = len(s)
    while cnt < ls and s[cnt] not in num_chars:
        cnt += 1

    lhs = s[0:cnt]
    s = s[cnt:]
    if d_sep == '':
        cnt = -1
    else:
        cnt = s.rfind(d_sep)

    if cnt > 0:
        rhs = d_sep + s[cnt + 1:]
        s = s[:cnt]
    else:
        rhs = ''

    splt = ''
    while s != '':
        splt = s[-3:] + t_sep + splt
        s = s[:-3]

    return lhs + splt[:-1] + rhs


class Validator(object):
    def is_empty(self, value):
        return value is None or isinstance(value, (str, unicode)) and not bool(value.strip())

    def to_python(self, value):
        if self.is_empty(value):
            return None
        return self._validate(self._to_python(value))

    def from_python(self, value):
        return self._from_python(value)

    def _to_python(self, value):
        return value

    def _from_python(self, value):
        return unicode(value)

    def _validate(self, value):
        return value


class Integer(Validator):
    """
    >>> i = Integer()
    >>> i.to_python('10')
    10
    >>> i = Integer(min=0, max=10)
    >>> i.to_python('0')
    0
    >>> i.to_python('10')
    10
    >>> i.to_python('-1')
    Traceback (most recent call last):
    ...
    ValidationException: Values must not be less than 0
    >>> i.to_python('11')
    Traceback (most recent call last):
    ...
    ValidationException: Value must not be greater than 10
    >>> i.to_python('c')
    Traceback (most recent call last):
    ...
    ValidationException: Please enter an integer - [c]

    """

    def __init__(self, min=None, max=None):
        self.min = min
        self.max = max

    def _to_python(self, value):
        if isinstance(value, (str, unicode)):
            value = value.replace(',', '')

        try:
            value = int(value)
        except ValueError:
            raise ValidationException('Please enter an integer - [%s]' % value)

        if self.min is not None and value is not None and value < self.min:
            raise ValidationException('Values must not be less than %d' % (self.min,))

        if self.max is not None and value > self.max:
            raise ValidationException('Value must not be greater than %d' % (self.max,))

        return value

    def _from_python(self, value):
        if isinstance(value, (int, float, long, decimal.Decimal)):
            return '%s' % split_thousands(int(value))
        else:
            return value


class Decimal(Validator):
    """
    >>> d = Decimal()
    >>> d.to_python('10.01')
    Decimal("10.01")
    >>> d.to_python('0')
    Decimal("0.00")
    >>> d = Decimal(min = 0, max = 10.01)
    >>> d.to_python('-1')
    Traceback (most recent call last):
    ...
    ValidationException: Value must not be less than 0
    >>> d.to_python('10.02')
    Traceback (most recent call last):
    ...
    ValidationException: Value must not be greater than 10
    >>> d.to_python('c')
    Traceback (most recent call last):
    ...
    ValidationException: Please enter a number - [c]
    """

    def __init__(self, min=None, max=None, rounding=decimal.ROUND_HALF_EVEN, scale=2):
        self.min = min
        self.max = max
        self.rounding = rounding
        self.scale = scale

    def _to_python(self, value):
        if isinstance(value, (str, unicode)):
            value = value.replace(',', '')
        try:
            if not isinstance(value, float):
                value = float(value)

            value = decimal.Decimal(('%%0.%df' % self.scale) % value)
        except ValueError:
            raise ValidationException('Please enter a number - [%s]' % value)

        if self.min is not None and value < decimal.Decimal(str(self.min)):
            raise ValidationException('Value must not be less than %d' % (self.min,))

        if self.max is not None and value > decimal.Decimal(str(self.max)):
            raise ValidationException('Value must not be greater than %d' % (self.max,))

        return value

    def _from_python(self, value):
        if isinstance(value, (float, int, decimal.Decimal)):
            if isinstance(value, float):
                value = '%f' % value
            return split_thousands(unicode(decimal.Decimal(value).quantize(decimal.Decimal('.' + ('0' * (self.scale - 1)) + '1'), rounding=self.rounding)))
        else:
            return value


class Currency(Decimal):
    """
    >>> c = Currency()
    >>> c.to_python('10.34')
    Decimal('10.34')
    >>> c.to_python('$10.34')
    Decimal('10.34')
    >>> c.to_python('$10.3')
    Decimal('10.30')
    >>> c.to_python('10.3')
    Decimal('10.30')
    >>> c.to_python('1,000.3')
    Decimal('1000.30')
    >>> c.to_python('$1,000.3')
    Decimal('1000.30')
    >>> c.to_python('$+1,000.3')
    Decimal('1000.30')
    >>> c.to_python('$-1,000.3')
    Decimal('-1000.30')
    >>> c.to_python('+$-1,000.3')
    Decimal('-1000.30')
    >>> c.to_python('-$1,000.3')
    Decimal('-1000.30')
    >>> c.to_python('-$-1,000.3')
    Decimal('-1000.30')
    >>> c.to_python('-$+1,000.3')
    Decimal('1000.30')
    >>> c.to_python('+$1,000.3')
    Decimal('1000.30')
    >>> c.to_python('c')
    Traceback (most recent call last):
    ...
    ValidationException: Please enter a number - [c]
    """
    _currency = re.compile(r'^(?P<sign1>[+-])?\$?(?P<sign2>[+-])?(?P<digits>\d*(?:,\d\d\d)*)(?P<cents>\.\d{1,2})?$', re.I)

    def is_empty(self, value):
        if value is None:
            return True
        value = unicode(value).strip()
        return value == '' or value == '$'

    def _to_python(self, value):
        if isinstance(value, (str, unicode)):
            match = self._currency.search(unicode(value))
            if not match:
                raise ValidationException('Please enter a number - [%s]' % value)
            d = match.groupdict()
            if not d['digits'] and not d['cents']:
                raise ValidationException('Please enter a number - [%s]' % value)
            sign = d['sign2'] or d['sign1'] or ''
            return Decimal._to_python(self, '%s%s%s' % (sign, d['digits'].replace(',', ''), d['cents'] or '.00'))

        else:
            return Decimal._to_python(self, value)

    def _from_python(self, value):
        if isinstance(value, (int, float, long, decimal.Decimal)):
            return '$%s' % Decimal._from_python(self, value)
        else:
            return value


class Unicode(Validator):
    """
    >>> u = Unicode(10)
    >>> u.to_python('hello')
    u'hello'
    >>> u.to_python('01234567890')
    Traceback (most recent call last):
    ...
    ValidationException: Please enter a string no more than 10 characters
    >>> u.to_python(123456789)
    u'123456789'
    """
    def __init__(self, min_length=None, max_length=None, truncate=False):
        self.min_length = min_length
        self.max_length = max_length
        self.truncate = truncate

    def _to_python(self, value):
        if not isinstance(value, (unicode)):
            if isinstance(value, str):
                value = unicode(value, errors='ignore')
            else:
                value = unicode(value)
        return value

    def _validate(self, value):
        if self.min_length and len(value) < self.min_length:
            raise MinLengthException('Please enter a string no shorter than than %d characters' % self.min_length)

        if self.max_length and not self.truncate and len(value) > self.max_length:
            raise MaxLengthException('Please enter a string no more than %d characters' % self.max_length)
        return value


class Enum(Unicode):
    """
    >>> e = Enum(['one', 'two', 'three'], 3)
    >>> e.to_python('one')
    u'one'
    >>> e.to_python('zero')
    Traceback (most recent call last):
    ...
    ValidationException: Valid choices are: one, two, three. You provided [zero]
    >>> from openmile.lib import enum
    >>> class E(enum.Enum):
    ...     A = '1'
    ...     B = '2'
    ...
    >>> e = Enum(E, 3)
    >>> e.to_python('1')
    u'1'
    """

    def __init__(self, choices, max_length=None, truncate=False):
        self.choices = choices
        if max_length is None and inspect.isclass(self.choices) and issubclass(self.choices, enum.Enum):
            max_length = self.choices.max_length()
        Unicode.__init__(self, max_length=max_length, truncate=truncate)

    def _to_python(self, value):
        value = Unicode._to_python(self, value).strip()

        if inspect.isclass(self.choices) and issubclass(self.choices, enum.Enum):
            choices = self.choices.keys()
        elif isinstance(self.choices, list):
            if isinstance(self.choices[0], (list, tuple)):
                choices = [x[0] for x in self.choices]
            else:
                choices = self.choices
        else:
            choices = self.choices

        if value not in choices:
            raise ValidationException('Valid choices are: %s. You provided [%s]' % (', '.join([unicode(c) for c in choices]), value))
        return value


class Date(Validator):
    """ There are about a billion tests that could be done here.
    >>> d = Date()
    >>> d.to_python('12/2/1989')
    datetime.date(1989, 12, 2)
    >>> d.to_python('01/02/1989')
    datetime.date(1989, 1, 2)
    >>> d.to_python('1989/01/02')
    datetime.date(1989, 1, 2)
    >>> d.to_python('13/01/1989')
    datetime.date(1989, 1, 13)
    >>> d.to_python('01/32/1989')
    Traceback (most recent call last):
    ...
    ValidationException: day is out of range for month
    >>> d.to_python('13/31/1989')
    Traceback (most recent call last):
    ...
    ValidationException: month must be in 1..12
    """
    def _to_python(self, value):
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        value = str(value)

        try:
            result = parse(value).date()
            if result.year < 1900:
                raise ValidationException('Year must be after 1900')
            return result
        except ValueError, e:
            raise ValidationException(e.message)

    def _from_python(self, value):
        if isinstance(value, (date, datetime)):
            return value.strftime('%m/%d/%Y')
        return value


class Time(Validator):
    """
    >>> t = Time()
    >>> t.to_python('13:45')
    datetime.time(13, 45)
    >>> t.to_python('13:60')
    Traceback (most recent call last):
    ...
    ValidationException: minute must be in 0..59
    >>> t.to_python('24:45')
    Traceback (most recent call last):
    ...
    ValidationException: hour must be in 0..23
    >>> t.to_python('5:45')
    datetime.time(5, 45)
    >>> t.to_python('1545')
    datetime.time(15, 45)
    >>> t.to_python('15:45:45')
    Traceback (most recent call last):
    ...
    ValidationException: Invalid time format, please use XX:XX
    """

    time_re = re.compile(r"^(\d{1,2}):?(\d\d)(:?\d\d)?(\s*AM|PM)?$", re.I)

    def _to_python(self, value):
        if isinstance(value, time):
            return value

        value = str(value)

        m = self.time_re.match(value)
        if not m:
            raise ValidationException('Invalid time format, please use XX:XX')
        value = '%s:%s' % (m.groups()[0], m.groups()[1])
        if m.groups()[2] is not None:
            value = '%s:%s' % (value, m.groups()[2].replace(':', ''))
        if m.groups()[3] is not None:
            value = '%s %s' % (value, m.groups()[3].strip())

        try:
            return parse(value).time()
        except ValueError, e:
            raise ValidationException(e.message)

    def _from_python(self, value):
        if isinstance(value, time):
            return value.strftime('%H:%M')
        return value


class DateTime(Validator):
    """
    >>> d = DateTime()
    >>> d.to_python('12/03/1989 5:45:52')
    datetime.datetime(1989, 12, 3, 5, 45, 52)
    >>> d.to_python('12/03/1989 5:45:60')
    Traceback (most recent call last):
    ...
    ValidationException: second must be in 0..59
    """

    def _to_python(self, value):
        if isinstance(value, datetime):
            return value

        value = str(value)

        try:
            return parse(value)
        except ValueError, e:
            raise ValidationException(e.message)

    def _from_python(self, value):
        if isinstance(value, (date, datetime)):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        return value


class Boolean(Validator):
    """
    >>> b = Boolean()
    >>> b.to_python(None)
    >>> b.to_python('None')
    >>> b.to_python(True)
    True
    >>> b.to_python(1)
    True
    >>> b.to_python('t')
    True
    >>> b.to_python('0')
    False
    >>> b.to_python('wtf')
    Traceback (most recent call last):
    ...
    ValidationException: Please enter "yes" or "no"
    """

    true_values = ['true', 't', 'yes', 'y', 'on', '1', 'yeah', 'yah', 'yup']
    false_values = ['false', 'f', 'no', 'n', 'off', '0', '2', 'nah', 'nope']
    none_values = ['none']

    def _to_python(self, value):
        if isinstance(value, (str, unicode)):
            value = value.strip().lower()
            if value in self.true_values:
                return True
            if not value or value in self.false_values:
                return False
            if value in self.none_values:
                return None

            raise ValidationException('Please enter "yes" or "no"')
        return bool(value)

    def _from_python(self, value):
        return str(value)


class Type(Integer):
    """Use for types where applicable (alert type, event type etc.) Likely indexed so use integer type.

    >>> t = Type([1, 2, 3])
    >>> t.to_python(1)
    1
    >>> t.to_python(4)
    Traceback (most recent call last):
    ...
    ValidationException: Valid choices are: 1,2,3. You provided [4]
    >>> from openmile.lib import enum
    >>> class E(enum.Enum):
    ...     A = 1
    ...     B = 2
    ...
    >>> t = Type(E)
    >>> t.to_python(1)
    1
    """
    def __init__(self, choices, min=None, max=None):
        self.choices = choices
        Integer.__init__(self, min=min, max=max)

    def _to_python(self, value):
        value = Integer._to_python(self, value)

        if inspect.isclass(self.choices) and issubclass(self.choices, enum.Enum):
            choices = self.choices.keys()
        else:
            if self.choices and isinstance(self.choices[0], tuple):
                choices = [x[0] for x in self.choices]
            else:
                choices = self.choices

        if value not in choices:
            raise ValidationException('Valid choices are: %s. You provided [%s]' % (','.join(map(lambda x: str(x), choices)), value))
        return value


class PhoneNumber(Unicode):
    """
    >>> p = PhoneNumber()
    >>> p.to_python(2234567890) # testing integer
    u'2234567890'
    >>> p.to_python('2234567890') # testing string
    u'2234567890'
    >>> p.to_python('223-456-7890') # testing typical phone number
    u'2234567890'
    >>> p.to_python('223-456-789o') # testing mixed letters
    Traceback (most recent call last):
    ...
    ValidationException: Please enter a 10 digit phone number with optional +country code in the format +#* ###-###-####
    >>> p.to_python('223  456  7890') # testing weird spacing
    u'2234567890'
    >>> p.to_python('+1-223-456-7890') # testing country code with +
    u'+12234567890'
    >>> p.to_python('1-223-456-7890') # testing country code missing +
    u'+12234567890'
    >>> p.to_python('112-456-7890') # area code can't start with 1
    Traceback (most recent call last):
    ...
    ValidationException: Please enter a 10 digit phone number with optional +country code in the format +#* ###-###-####

    >>> p.from_python('+12234567890')
    '+1 (223) 456-7890'
    >>> p.from_python('+442234567890')
    '+44 (223) 456-7890'
    >>> p.from_python('442234567890') # No plus, ignored
    '442234567890'
    >>> p.from_python('2345678901')
    '(234) 567-8901'
    >>> p.from_python('2345637') # Unrecognized length, ignored
    '2345637'
    """
    _phoneRE = re.compile(r"""
                    # don't match beginning of string, number can start anywhere
        (\d*)       # can optionally start with country code digits
        \D*         # optional separator
        ([2-9]\d{2})     # area code is 3 digits starting with 2-9 (e.g. '800')
        \D*         # optional separator is any number of non-digits
        (\d{3})     # trunk is 3 digits (e.g. '555')
        \D*         # optional separator
        (\d{4})     # rest of number is 4 digits (e.g. '1212')
        $           # end of string
        """, re.VERBOSE)
    # the following is to deal with things like 000-000-0000, especially in RMIS Carrier data
    _phonezeroRE = re.compile(r"""
                    # don't match beginning of string, number can start anywhere
        ([0]{3})    # area code is 3 digits starting with 2-9 (e.g. '800')
        \D*         # optional separator is any number of non-digits
        ([0]{3})    # trunk is 3 digits (e.g. '555')
        \D*         # optional separator
        ([0]{4})    # rest of number is 4 digits (e.g. '1212')
        $           # end of string
        """, re.VERBOSE)

    def __init__(self, max_length=16, truncate=False):
        Unicode.__init__(self, max_length=max_length, truncate=truncate)

    def is_empty(self, value):
        value = Unicode._to_python(self, value or '')
        match = self._phonezeroRE.search(value)
        if match:
            return True
        else:
            return Unicode.is_empty(self, value)

    def _to_python(self, value):
        value = Unicode._to_python(self, value)
        match = self._phoneRE.search(value)
        if not match:
            raise ValidationException('Please enter a 10 digit phone number with optional +country code in the format +#* ###-###-####')

        python_number = ''.join(filter(None, match.groups()))
        if match.groups(0) is not None:
            # International number
            python_number = '+' + python_number

        return python_number

    def _from_python(self, value):
        if not isinstance(value, (str, unicode)):
            return value

        international_prefix = None
        if value[0] == '+':
            if len(value) < 12:
                return value  # Needs at least + and a country code
            international_prefix = value[:-10]
            value = value[-10:]
        elif len(value) != 10:
            # Too many or few digits
            return value

        phone_number = '(%s) %s-%s' % (value[:3], value[3:6], value[6:])

        if international_prefix:
            phone_number = '%s %s' % (international_prefix, phone_number)

        return phone_number


class Email(Unicode):
    """

    >>> e = Email()
    >>> e.to_python('glen_chiacchieri123@sub1.openmile.com') # testing typical email
    u'glen_chiacchieri123@sub1.openmile.com'
    >>> e.to_python('glen.+c@sub.openmile.com') # testing a couple weird chars
    u'glen.+c@sub.openmile.com'
    >>> e.to_python('glen@c@sub.openmile.com') # testing two @s
    Traceback (most recent call last):
    ...
    ValidationException: The domain portion of the email address is invalid (the portion after the @: c@sub.openmile.com)

    >>> e.to_python('glen@sub.openmileabsurdlylonganduselessdomainwhichshouldfailohmygoodnessyes.com') # testing long domain
    Traceback (most recent call last):
    ...
    ValidationException: The domain portion of the email address is invalid (the portion after the @: sub.openmileabsurdlylonganduselessdomainwhichshouldfailohmygoodnessyes.com)
    >>> e.to_python('glen') # testing totally wrong format
    Traceback (most recent call last):
    ...
    ValidationException: Please enter an email address in the form user@domain.com
    >>> e.to_python('glen ch@openmil.com') # testing username wrong
    Traceback (most recent call last):
    ...
    ValidationException: The username portion of the email address is invalid (the portion before the @: glen ch)


    """

    # http://en.wikipedia.org/wiki/Email_address#Local_part
    # special characters are rarely used and discouraged
    special_characters = [32, 34, 40, 41, 44, 58, 59, 60, 62, 64, (91, 93)]  # "(),:;<>@[\]
    local_part_constraints = [(65, 90),  # a-z
                              (97, 122),  # A-Z
                              (48, 57),  # 0-9
                              33, (35, 39), 42, 43, 45, 47, 61, 63, (94, 96), (123, 126),  # !#$%&'*+-/=?^_`{|}~
                              46,  # .
                              ]
    domainRE = re.compile(r"""
        ^(?:[a-z0-9][a-z0-9\-]{0,62}\.)+ # (sub)domain - alpha followed by 62max chars (63 total)
        [a-z]{2,}$                       # TLD
    """, re.I | re.VERBOSE)

    def __init__(self, max_length=255, truncate=False):
        Unicode.__init__(self, max_length=max_length, truncate=truncate)

        self.char_index = {}
        for v in self.local_part_constraints:
            if isinstance(v, int):
                self.char_index[v] = True
            elif isinstance(v, tuple):
                for v1 in range(v[0], v[1] + 1):
                    self.char_index[v1] = True

    def _check_username(self, value):
        for x in value:
            if not self.char_index.get(ord(x), False):
                return False

        if value.startswith('.') or value.endswith('.'):
            return False
        elif value.find('..') != -1:
            return False
        return True

    def _to_python(self, value):
        value = Unicode._to_python(self, value).strip()
        splitted = value.split('@', 1)
        try:
            username, domain = splitted
        except ValueError:
            raise ValidationException('Please enter an email address in the form user@domain.com')

        if not self._check_username(username):
            raise ValidationException('The username portion of the email address is invalid (the portion before the @: %s)' % username)

        if not self.domainRE.search(domain):
            raise ValidationException('The domain portion of the email address is invalid (the portion after the @: %s)' % domain)

        return value


# Represents the value another table/objects PrimaryID. Similar to ForeignKey but does not enforce constraint.
class ObjectID(Integer):
    """

    >>> o = ObjectID()
    >>> o.to_python(2) # testing normal integer
    2
    >>> o.to_python('2') # testing string
    2
    >>> o.to_python(0) # testing less than min
    Traceback (most recent call last):
    ...
    ValidationException: Values must not be less than 1

    """

    def __init__(self, min=1, max=None):
        Integer.__init__(self, min=min, max=max)

    def _from_python(self, value):
        if isinstance(value, (int, float, long, decimal.Decimal)):
            return '%d' % int(value)
        else:
            return value


class ZipCode5(Unicode):
    """

    >>> z = ZipCode5()
    >>> z.to_python('02115') # testing normal string zip
    u'02115'
    >>> z.to_python(12115) # testing integer zip
    u'12115'
    >>> z.to_python('1234') # testing too short, cuts off anything after 5 digits
    Traceback (most recent call last):
    ...
    ValidationException: Please enter ZipCode as a 5 digit number - [1234]

    >>> z.to_python('123456') # testing too long, cuts off anything after 5 digits
    u'12345'
    >>> z.to_python('o2115') # testing mixed zip
    Traceback (most recent call last):
    ...
    ValidationException: Please enter ZipCode as a 5 digit number - [o2115]
    """

    _zipcode5 = re.compile(r'^(\d\d\d\d\d)', re.I)

    def __init__(self, max_length=5, truncate=False):
        Unicode.__init__(self, max_length=max_length, truncate=truncate)

    def _to_python(self, value):
        value = Unicode._to_python(self, value)

        match = self._zipcode5.search(value)
        if not match:
            raise ValidationException('Please enter zip code as a 5 digit number - [%s]' % value)
        return match.groups()[0]


class ZipCodeExt(Unicode):
    """

    >>> z = ZipCodeExt()
    >>> z.to_python('1234')  # testing normal string zip
    u'1234'
    >>> z.to_python(1234)    # testing integer zip
    u'1234'
    >>> z.to_python('123')   # testing too short
    Traceback (most recent call last):
    ...
    ValidationException: Please enter ZipCodeExt as a 4 digit number - [123]
    >>> z.to_python('12345') # testing too long
    u'1234'
    >>> z.to_python('o123')  # testing mixed zip
    Traceback (most recent call last):
    ...
    ValidationException: Please enter ZipCodeExt as a 4 digit number - [o123]
    """

    _zipcodeext = re.compile(r'^(\d\d\d\d)', re.I)

    def __init__(self, max_length=4, truncate=False):
        Unicode.__init__(self, max_length=max_length, truncate=truncate)

    def _to_python(self, value):
        value = Unicode._to_python(self, value)

        match = self._zipcodeext.search(value)
        if not match:
            raise ValidationException('Please enter ZipCodeExt as a 4 digit number - [%s]' % value)
        return match.groups()[0]


class PhoneExt(Unicode):
    """

    >>> p = PhoneExt()
    >>> p.to_python('1234')    # testing string
    u'1234'
    >>> p.to_python(1234)      # testing int
    u'1234'
    >>> p.to_python(0234)      # testing int, treats this as octal
    u'156'
    >>> p.to_python('')       # testing too short
    Traceback (most recent call last):
    ...
    ValidationException: Please enter extension as a 1-6 digit number - []
    >>> p.to_python('1234567') # testing too long, should cut off after 6
    u'123456'
    """

    _phoneext = re.compile(r'^(\d{1,6})', re.I)

    def __init__(self, max_length=6, truncate=False):
        Unicode.__init__(self, max_length=max_length, truncate=truncate)

    def _to_python(self, value):
        value = Unicode._to_python(self, value)

        match = self._phoneext.search(value)
        if not match:
            raise ValidationException('Please enter extension as a 1-6 digit number - [%s]' % value)
        return match.groups()[0]


class Percentage(Decimal):
    """
    >>> p = Percentage()
    >>> p.to_python(0)
    Decimal('0.00')
    >>> p.to_python('-100')
    Decimal('-100.00')
    >>> p.to_python('100')
    Decimal('100.00')
    >>> p.to_python('5%')
    Decimal('5.00')
    """

    def _to_python(self, value):
        if isinstance(value, basestring):
            value = re.sub(r"(.*?)( *?% *$)", r'\1', value)
        return Decimal._to_python(self, value)
