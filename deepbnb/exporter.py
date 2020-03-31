import openpyxl

from scrapy.exporters import BaseItemExporter


class XlsxItemExporter(BaseItemExporter):
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

        # Make name into a hyperlink
        item['name'] = '=HYPERLINK("https://www.airbnb.com/rooms/{}", "{}")'.format(
            item['id'], item.get('name', item['id'])),

        fields = self._get_serialized_fields(item, default_value='', include_empty=True)
        values = tuple(self._build_row(x for _, x in fields))
        self._worksheet.append(values)

    def finish_exporting(self):
        self._workbook.save(self._filename)

    def serialize_field(self, field, name, value):
        serializer = field.get('serializer', self._join_if_needed)
        return serializer(value)

    @staticmethod
    def _build_row(values):
        for s in values:
            yield s

    def _join_if_needed(self, value):
        if isinstance(value, (list, tuple)):
            try:
                return self._join_multivalued.join(value)
            except TypeError:  # list in value may not contain strings
                pass
        return value

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
