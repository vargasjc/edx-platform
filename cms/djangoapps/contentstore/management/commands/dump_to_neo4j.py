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

    Until, of course, we add bulk import to py2neo :)

    """
    # {<block_type>: [<field_name>]}
    field_names_by_type = {}
    csv_dir = "coursegraph2"
    neo4j_root = ""

    def serialize_item(self, item, course_key):
        # convert all fields to a dict and filter out parent and children field
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

        return fields, block_type

    def serialize_items(items, course_key):
        blocks_by_type = defaultdict(list)
        for item in items:
            serialized_item, block_type = self.serialize_item(item, course.id)
            blocks_by_type[block_type].append(serialized_item)

        return blocks_by_type



    def get_relationships_from_items(self, items):
        relationships = []
        for item in items:
            if item.has_children:
                for child in item.children:
                    parent_loc = unicode(item.location)
                    child_loc = unicode(child)
                    relationships.append([parent_loc, child_loc])
        return relationships




    def handle(self, *args, **options):

        all_courses = modulestore().get_course_summaries()
        number_of_courses = len(all_courses)

        for index, course in enumerate(all_courses):

            items = modulestore().get_items(course.id)
            print u"dumping {} (course {}/{}) ({} items)".format(
                course.id, index + 1, number_of_courses, len(items)
            )

            blocks_by_type = self.serialize_items(items, course.id)

            relationships = self.get_relationships_from_items(items)

            self.add_block_info_to_csvs(blocks_by_type)

            self.add_to_relationship_csv(relationships)

        print self.field_names_by_type.keys()

        print "finished exporting modulestore data to csv"
        print "now run the following command to import these data into noo4j:"
        print self.generate_bulk_import_command()


    def add_to_relationship_csv(self, relationships):
        rows = [] if create else []
        rows.extend(relationships)
        with open('coursegraph2/relationships.csv', 'a') as csvfile:
            # if this file hasn't been written to yet, add a header
            writer = csv.writer(output_file)
            if csvfile.tell() == 0:
                writer.writerow([':START_ID', ':END_ID'])

            writer.writerows(rows)


    def _write_results_to_csv(self, rows, writer):
        """
        Writes each row to a CSV file.
        Fields are separated by tabs, no quote character.
        Output would be encoded as utf-8.
        """
        writer.writerows(rows)


    def _normalize_value(self, value):
        if value is None:
            value = 'NULL'
        value = unicode(value).encode('utf-8')
        # neo4j has an annoying thing where it freaks out if a field begins
        # with a quotation mark
        while value.startswith('"') or value.startswith("'"):
            value = value.strip('"')
            value = value.strip("'")

        return value

    def get_field_names_for_type(block_type, serialized_xblocks):
        field_names = self.field_names_by_type.get(block_type)
        if field_names is None:
            field_names = serialized_xblocks[0].keys()
            field_names.remove('type:LABEL') ## this needs to be first for some reason
            field_names = ['type:LABEL'] + field_names
            self.field_names_by_type[block_type] = field_names

        return field_names

    def add_block_info_to_csvs(self, blocks_by_type):
        for block_type, serialized_xblocks in blocks_by_type.iteritems():
            field_names = self.get_field_names_for_type(block_type, serialized_xblocks)

            rows = []
            for serialized in serialized_xblocks:
                row = [
                    self._normalize_value(serialized[field_name])
                    for field_name
                    in field_names
                ]
                rows.append(row)

            with open(self.csv_dir + '/{}.csv'.format(block_type), 'a') as csvfile:
                writer = csv.writer(csvfile)
                if csvfile.tell() == 0:
                    writer.writerow(field_names)
                writer.writerows(rows)


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
