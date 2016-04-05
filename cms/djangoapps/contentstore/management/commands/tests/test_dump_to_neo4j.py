from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase
from contentstore.management.commands.dump_to_neo4j import ModuleStoreSerializer
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from xmodule.modulestore.django import modulestore
import tempfile
import shutil
import os
import csv
import ddt

BLOCK_TYPES = [
    'about',
    'course',
    'chapter',
    'sequential',
    'vertical',
    'html',
    'problem',
    'video'
]

@ddt.ddt
class TestModuleStoreSerializer(SharedModuleStoreTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestModuleStoreSerializer, cls).setUpClass()
        cls.course = CourseFactory.create()
        cls.chapter = ItemFactory.create(parent=cls.course, category='chapter')
        cls.sequential = ItemFactory.create(parent=cls.chapter, category='sequential')
        cls.vertical = ItemFactory.create(parent=cls.sequential, category='vertical')
        cls.html = ItemFactory.create(parent=cls.vertical, category='html')
        cls.problem = ItemFactory.create(parent=cls.vertical, category='problem')
        cls.video = ItemFactory.create(parent=cls.vertical, category='video')

    def setUp(self):
        self.csv_dir = tempfile.mkdtemp("csv")
        self.neo4j_root = tempfile.mkdtemp("neo4j")

        # Clean temp directories
        self.addCleanup(shutil.rmtree, self.csv_dir)
        self.addCleanup(shutil.rmtree, self.neo4j_root)

    def test_serialize_items(self):
        # test that the serialize_items method works as expected
        modulestore_serializer = ModuleStoreSerializer(self.csv_dir, self.neo4j_root)
        items = modulestore().get_items(self.course.id)
        blocks_by_type = modulestore_serializer.serialize_items(items, self.course.id)
        self.assertItemsEqual(
            blocks_by_type.keys(),
            BLOCK_TYPES
        )
        # one course
        self.assertEqual(len(blocks_by_type['course']), 1)
        serialized_course = blocks_by_type['course'][0]
        # that course has the correct fields set on it
        self.assertEqual(serialized_course['course_key'], unicode(self.course.id))
        self.assertFalse(serialized_course['self_paced'])

    def test_csvs_written(self):
        mds = ModuleStoreSerializer(self.csv_dir, self.neo4j_root)
        mds.dump_to_csv()
        self.assertItemsEqual(
            os.listdir(self.csv_dir),
            [block_type + ".csv" for block_type in BLOCK_TYPES] + ['relationships.csv']
        )

    @ddt.data(*BLOCK_TYPES)
    def test_course_csv(self, block_type):
        mds = ModuleStoreSerializer(self.csv_dir, self.neo4j_root)
        mds.dump_to_csv()
        filename = self.csv_dir + "/{block_type}.csv".format(block_type=block_type)
        with open(filename) as block_type_csvfile:
            rows = list(csv.reader(block_type_csvfile))

        self.assertEqual(len(rows), 2)

        header = rows[0]
        self.assertEqual(header[0], "type:LABEL")
        body = rows[1]
        self.assertEqual(body[0], block_type)
