def duration(value):
    ONE_SECOND = 1000
    ONE_MINUTE = ONE_SECOND * 60

    if not value:
        return '0 s'

    abs_value = abs(value)

    if abs_value < 3 * ONE_SECOND:
        return '%d ms' % (value,)
    elif abs_value < 5 * ONE_MINUTE:
        return '%d s' % (value / ONE_SECOND,)
    else:
        return '%d m' % (value / ONE_MINUTE,)
