import csv

from django.core.management.base import BaseCommand
from xmodule.modulestore.django import modulestore
from collections import defaultdict
import gc
import os


class Command(BaseCommand):
    """
    Generates CSVs to be used with neo4j's csv import tool (this is much
    faster for bulk importing than using py2neo, which updates neo4j over
    a REST api)
    """
    help = '''
    Here's an example neo4j-import command:

    ./bin/neo4j-import --id-type string --nodes:chapter chapter.csv \
    --nodes:discussion discussion.csv --nodes:html html.csv \
    --nodes:openassessment openassessment.csv
    --nodes:problem problem.csv \
    --nodes:sequential sequential.csv --nodes:vertical vertical.csv \
    --nodes:video video.csv --nodes:course course.csv \
    --relationships:PARENT_OF relationships.csv \
    --into data/coursegraph-demo \
    --multiline-fields=true

    (This could be refactored to automatically generate which nodes files
    to use based off of csv files present in a directory)
    '''

    # {<block_type>: [<field_name>]}
    field_names_by_type = {}


    def handle(self, *args, **options):

        all_courses = modulestore().get_courses()
        number_of_courses = len(all_courses)

        for index, course in enumerate(all_courses):
            # {<block_type>: [<block>]}
            blocks_by_type = defaultdict(list)

            relationships = []

            items = modulestore().get_items(course.id)
            print u"dumping {} (course {}/{}) ({} items)".format(
                course.id, index + 1, number_of_courses, len(items)
            )


            for item in items:

                # convert all fields to a dict and filter out parent field
                fields = dict(
                    (field, field_value.read_from(item))
                    for (field, field_value) in item.fields.iteritems()
                    if field not in ['parent', 'children']
                )

                fields['edited_on'] = unicode(getattr(item, 'edited_on', u''))
                fields['display_name'] = item.display_name_with_default

                fields['location:ID'] = unicode(item.location)
                if "location" in fields:
                    del fields['location']

                block_type = item.scope_ids.block_type

                fields['type'] = block_type

                fields['type:LABEL'] = fields['type']
                del fields['type']

                if 'checklists' in fields:
                    del fields['checklists']

                fields['org'] = course.id.org
                fields['course'] = course.id.course
                fields['run'] = course.id.run
                fields['course_key'] = unicode(course.id)

                blocks_by_type[block_type].append(fields)

            for item in items:
                if item.has_children:
                    for child in item.children:
                        parent_loc = unicode(item.location)
                        child_loc = unicode(child)
                        relationships.append([parent_loc, child_loc])


            self.add_to_csvs_from_blocks(blocks_by_type)

            self.add_to_relationship_csv(relationships, index==0)

        print self.field_names_by_type.keys()

        print "DONE"


    def add_to_relationship_csv(self, relationships, create=False):
        rows = [[':START_ID', ':END_ID']] if create else []
        rows.extend(relationships)
        mode = 'w' if create else 'a'
        with open('/tmp/relationships.tsv', mode) as csvfile:
            self._write_results_to_tsv(rows, csvfile)


    def _write_results_to_tsv(self, rows, output_file):
        """
        Writes each row to a TSV file.
        Fields are separated by tabs, no quote character.
        Output would be encoded as utf-8.
        All embeded tabs(\t), newlines(\n), and carriage returns(\r) are escaped.
        """

        writer = csv.writer(output_file, delimiter="\t", quoting=csv.QUOTE_NONE, quotechar='', lineterminator='\n')
        converted_rows = []
        for row in rows:
            converted_row = [self._normalize_value(val) for val in row]
            converted_rows.append(converted_row)
        writer.writerows(converted_rows)


    def _normalize_value(self, value):
        if value is None: value='NULL'
        value = unicode(value).encode('utf-8').replace('\\', '\\\\').replace('\r', '\\r').replace('\t','\\t').replace('\n', '\\n')
        while value.startswith('"') or value.startswith("'"):
            value = value.strip('"')
            value = value.strip("'")

        return value


    def add_to_csvs_from_blocks(self, blocks_by_type):

        for block_type, fields_list in blocks_by_type.iteritems():
            create = False
            field_names = self.field_names_by_type.get(block_type)
            if field_names is None:
                field_names = fields_list[0].keys()
                field_names.remove('type:LABEL')
                field_names = ['type:LABEL'] + field_names
                self.field_names_by_type[block_type] = field_names
                create = True

            rows = [field_names] if create else []

            for fields in fields_list:
                row = [unicode(fields[field_name]) for field_name in field_names]
                rows.append(row)

            mode = 'w' if create else 'a'
            with open('/tmp/{}.tsv'.format(block_type), mode) as csvfile:
                self._write_results_to_tsv(rows, csvfile)


