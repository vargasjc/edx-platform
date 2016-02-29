import csv

from django.core.management.base import BaseCommand
from xmodule.modulestore.django import modulestore
from collections import defaultdict
import gc
import os


class Command(BaseCommand):
    """
    Generates TSVs to be used with neo4j's csv import tool (this is much
    faster for bulk importing than using py2neo, which updates neo4j over
    a REST api)


    """
    # {<block_type>: [<field_name>]}
    field_names_by_type = {}
    csv_dir = "coursegraph2"
    neo4j_root = ""

    def serialize_item(self, item, course_key):


    def handle(self, *args, **options):

        all_courses = modulestore().get_course_summaries()
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

        print "finished exporting modulestore data to csv"
        print "now run the following command to import these data into noo4j:"
        print self.generate_bulk_import_command()


    def add_to_relationship_csv(self, relationships, create=False):
        rows = [[':START_ID', ':END_ID']] if create else []
        rows.extend(relationships)
        with open('coursegraph2/relationships.csv', 'a') as csvfile:
            self._write_results_to_csv(rows, csvfile)


    def _write_results_to_csv(self, rows, output_file):
        """
        Writes each row to a TSV file.
        Fields are separated by tabs, no quote character.
        Output would be encoded as utf-8.
        """

        writer = csv.writer(output_file)
        converted_rows = []
        for row in rows:
            converted_row = [self._normalize_value(val) for val in row]
            converted_rows.append(converted_row)
        writer.writerows(converted_rows)


    def _normalize_value(self, value):
        if value is None: value='NULL'
        value = unicode(value).encode('utf-8')
        # neo4j has an annoying thing where it freaks out if a field begins
        # with a quotation mark
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

            with open(self.csv_dir + '/{}.csv'.format(block_type), 'a') as csvfile:
                self._write_results_to_csv(rows, csvfile)


    def generate_bulk_import_command(self):
        """
        Generates the command to be used for
        """

        command = "{neo4j_root}/bin/neo4j-import --id-type string"
        for filename in os.listdir(self.csv_dir):
            if filename.endswith(".csv") and filename != "relationships.csv":
                name = filename[:-4]  # cut off .csv
                node_info = " --nodes:{name} coursegraph2/{filename}".format(
                    name=name, filename=filename
                )
                command += node_info

        command += " --relationships:PARENT_OF relationships.csv"
        command += " --into {neo4j_root}/data/coursegraph-demo"
        command += " --multiline-fields=true"
        command += " --quote=''"
        # command += " --delimiter=TAB"
        # we need to set --bad-tolerance because old mongo has a lot of
        # dangling pointers
        command += " --bad-tolerance=1000000"
        return command.format(neo4j_root=self.neo4j_root)
