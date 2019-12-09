import openpyxl
import six

from scrapy.exporters import BaseItemExporter


class AirbnbExcelItemExporter(BaseItemExporter):
    """Export items to Excel spreadsheet."""

    def __init__(self, file, include_headers_line=True, join_multivalued=',', **kwargs):
        """Class constructor."""
        # fields_to_export = settings.get('FIELDS_TO_EXPORT', [])
        # if fields_to_export:
        #     kwargs['fields_to_export'] = fields_to_export

        super().__init__(**kwargs)

        self.include_headers_line = include_headers_line
        self._workbook = openpyxl.workbook.Workbook()
        self._worksheet = self._workbook.active
        self._headers_not_written = True
        self._join_multivalued = join_multivalued
        self._filename = file.name
        file.close()

    def export_item(self, item):
        if self._headers_not_written:
            self._headers_not_written = False
            self._write_headers_and_set_fields_to_export(item)

        fields = self._get_serialized_fields(item, default_value='', include_empty=True)
        values = tuple(self._build_row(x for _, x in fields))
        self._worksheet.append(values)

    def finish_exporting(self):
        self._workbook.save(self._filename)

    def serialize_field(self, field, name, value):
        serializer = field.get('serializer', self._join_if_needed)
        return serializer(value)

    def _join_if_needed(self, value):
        if isinstance(value, (list, tuple)):
            try:
                return self._join_multivalued.join(value)
            except TypeError:  # list in value may not contain strings
                pass
        return value

    def _build_row(self, values):
        for s in values:
            try:
                yield self._to_native_str(s)
            except TypeError:
                yield s

    def _to_native_str(self, text, encoding=None, errors='strict'):
        return self._to_unicode(text, encoding, errors)

    @staticmethod
    def _to_unicode(text, encoding=None, errors='strict'):
        """Return the unicode representation of a bytes object `text`. If `text` is already an unicode object, return it
         as-is.
         """
        if isinstance(text, six.text_type):
            return text
        if not isinstance(text, (bytes, six.text_type)):
            raise TypeError('to_unicode must receive a bytes, str or unicode '
                            'object, got %s' % type(text).__name__)
        if encoding is None:
            encoding = 'utf-8'
        return text.decode(encoding, errors)

    def _write_headers_and_set_fields_to_export(self, item):
        if self.include_headers_line:
            if not self.fields_to_export:
                if isinstance(item, dict):
                    # for dicts try using fields of the first item
                    self.fields_to_export = list(item.keys())
                else:
                    # use fields declared in Item
                    self.fields_to_export = list(item.fields.keys())
            row = tuple(self._build_row(self.fields_to_export))
            self._worksheet.append(row)
