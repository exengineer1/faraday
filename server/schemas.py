import time
from marshmallow import fields
from marshmallow.exceptions import ValidationError


class JSTimestampField(fields.Field):
    """A field to serialize datetime objects into javascript
    compatible timestamps (like time.time()) * 1000"""

    def _serialize(self, value, attr, obj):
        if value is not None:
            return int(time.mktime(value.timetuple()) * 1000)


class PrimaryKeyRelatedField(fields.Field):
    def __init__(self, field_name='id', *args, **kwargs):
        self.field_name = field_name
        self.many = kwargs.get('many', False)
        super(PrimaryKeyRelatedField, self).__init__(*args, **kwargs)

    def _serialize(self, value, attr, obj):
        if self.many:
            ret = []
            for item in value:
                ret.append(getattr(item, self.field_name))
            return ret
        else:
            if value is None:
                return None
            return getattr(value, self.field_name)


class SelfNestedField(fields.Field):
    """A field to make namespaced schemas. It allows to have
    a field whose contents are the dump of the same object with
    other schema"""

    # Required because the target attribute will probably not exist
    _CHECK_ATTRIBUTE = False

    def __init__(self, target_schema, *args, **kwargs):
        self.target_schema = target_schema
        super(SelfNestedField, self).__init__(*args, **kwargs)

    def _serialize(self, value, attr, obj):
        ret, errors = self.target_schema.dump(obj)
        if errors:
            raise ValidationError(errors, data=ret)
        return ret

    def _deserialize(self, value, attr, data):
        raise NotImplementedError("Only dump is implemented for now")


class MutableField(fields.Field):
    """
    A field that enables the use of different fields for read and write.

    This is useful in many cases, like for example when you want to use a
    Nested field to show the data but an Integer field (that uses to be a
    primary key) for writing/deserializing.
    """

    # TODO: inherit required and other properties from the child fields

    def __init__(self, read_field, write_field, **kwargs):
        self.read_field = read_field
        self.write_field = write_field

        # Set _CHECK_ATTRIBUTE based on the read field because it is used
        # during serialization
        self._CHECK_ATTRIBUTE = self.read_field._CHECK_ATTRIBUTE

        # Propagate required=True to the children fields
        if kwargs.get('required'):
            self.read_field.required = self.write_field.required = True

        super(MutableField, self).__init__(**kwargs)

    def _serialize(self, value, attr, obj):
        return self.read_field._serialize(value, attr, obj)

    def _deserialize(self, value, attr, data):
        return self.write_field._deserialize(value, attr, data)

    def _add_to_schema(self, field_name, schema):
        # Propagate to child fields
        super(MutableField, self)._add_to_schema(field_name, schema)
        self.read_field._add_to_schema(field_name, schema)
        self.write_field._add_to_schema(field_name, schema)
