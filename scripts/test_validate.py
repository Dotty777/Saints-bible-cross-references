"""Exercise authenticated archives, embedded labels, and repeated source sections."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import validate


class ArchivedDanielTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.root_patch=patch.object(validate,'ROOT',self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.document={'book':'Daniel','chapters':[
            {'chapter':n,'section':n,'title':f'Daniel {n}',
             'verses':[{'reference':f'Daniel {n}:1','id':f'v{n}-1','text':f'Chapter {n} original body.'}]}
            for n in range(1,13)]}
        self.document['chapters'] += [
            {'chapter':13,'section':13,'title':'Daniel — Susanna','verses':[
                {'reference':'Susanna 1:7–8','id':'s7-8','text':'Composite original body.',
                 'continuation_paragraphs':['Original continuation.']},
                {'reference':'Susanna 1:35a','id':'s35a','text':'Original lettered unit.'}]},
            {'chapter':14,'section':14,'title':'Daniel — Bel and the Dragon','verses':[
                {'reference':'Bel and Dragon 1:15–17','id':'b15-17','text':'Original composite body.'}]}]

    def archive(self,document=None):
        document=self.document if document is None else document
        raw=(json.dumps(document,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
        path=self.root/'inputs'/'daniel.json'
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(raw)
        manifest={'source_commit':'a'*40,'input_archive':'inputs',
                  'archived_input_files':[{'file':'daniel.json','sha256':hashlib.sha256(raw).hexdigest()}]}
        folder=self.root/'review-batches'
        folder.mkdir(exist_ok=True)
        (folder/'test.json').write_text(json.dumps(manifest),encoding='utf-8')
        edge={'target':'Daniel 3:1','review_batch':'test',
              'target_source':{'commit':'a'*40,'blob_sha':validate.blob_digest(raw)}}
        return edge,path

    def test_authenticated_full_book_preserves_embedded_units_and_canonical_identity(self):
        edge,path=self.archive()
        raw=path.read_bytes()
        chapters,units=validate.archived_target_book(edge,'Daniel',{})
        expected=[v for c in self.document['chapters'] for v in c['verses']]
        self.assertEqual(list(units),[v['reference'] for v in expected])
        self.assertEqual(list(units.values()),expected)
        self.assertEqual(chapters['13'],['Susanna 1:7–8','Susanna 1:35a'])
        self.assertEqual(chapters['14'],['Bel and Dragon 1:15–17'])
        self.assertEqual(validate.ordered_range(chapters['3'],'Daniel 3:1','Daniel 3:1'),['Daniel 3:1'])
        self.assertEqual(edge['target'].rsplit(' ',1)[0],'Daniel')
        self.assertEqual(path.read_bytes(),raw)
        with self.assertRaisesRegex(ValueError,'expected full book'):
            validate.archived_target_book(edge,'Susanna',{})

    def test_alias_requires_correct_canonical_book_chapter_section_and_title(self):
        for chapter_index in [12,13]:
            for field,value in [('chapter',15),('section',15),('title','Unrelated section')]:
                with self.subTest(chapter_index=chapter_index,field=field):
                    document=copy.deepcopy(self.document)
                    document['chapters'][chapter_index][field]=value
                    edge,_=self.archive(document)
                    with self.assertRaisesRegex(ValueError,'unit reference'):
                        validate.archived_target_book(edge,'Daniel',{})
        document=copy.deepcopy(self.document)
        document['book']='Ezekiel'
        for chapter in document['chapters'][:12]:
            chapter['verses'][0]['reference']=chapter['verses'][0]['reference'].replace('Daniel','Ezekiel')
        edge,_=self.archive(document)
        with self.assertRaisesRegex(ValueError,'unit reference'):
            validate.archived_target_book(edge,'Ezekiel',{})

    def test_foreign_empty_wrong_section_and_duplicate_references_rejected(self):
        for reference in ['',None,'Judith 1:1','Susanna 2:1','Bel and Dragon 1:1','Susanna 1:','Susanna 1:7–8']:
            with self.subTest(reference=reference):
                document=copy.deepcopy(self.document)
                document['chapters'][12]['verses'][1]['reference']=reference
                edge,_=self.archive(document)
                with self.assertRaisesRegex(ValueError,'unit reference'):
                    validate.archived_target_book(edge,'Daniel',{})
        document=copy.deepcopy(self.document)
        document['chapters'][0]['verses'][0]['reference']='Susanna 1:6'
        edge,_=self.archive(document)
        with self.assertRaisesRegex(ValueError,'unit reference'):
            validate.archived_target_book(edge,'Daniel',{})

    def test_modified_raw_bytes_bad_blob_and_commit_are_rejected(self):
        edge,path=self.archive()
        path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'SHA256 mismatch'):
            validate.archived_target_book(edge,'Daniel',{})
        edge,_=self.archive()
        edge['target_source']['blob_sha']='b'*40
        with self.assertRaisesRegex(ValueError,'Pinned target blob differs'):
            validate.archived_target_book(edge,'Daniel',{})
        edge,_=self.archive()
        edge['target_source']['commit']='b'*40
        with self.assertRaisesRegex(ValueError,'commit mismatch'):
            validate.archived_target_book(edge,'Daniel',{})
        edge,path=self.archive()
        cache={}
        validate.archived_target_book(edge,'Daniel',cache)
        del cache[('test',edge['target_source']['commit'],edge['target_source']['blob_sha'])]
        path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'bytes changed'):
            validate.archived_target_book(edge,'Daniel',cache)


class ArchivedRepeatedChapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.root_patch=patch.object(validate,'ROOT',self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.document={'book':'Proverbs','chapters':[
            {'chapter':24,'section':1,'verses':[
                {'reference':'Proverbs 24:22e','id':'p24-22e','text':'First section body.'},
                {'reference':'Proverbs 24:22f','id':'p24-22f','text':'Lettered original body.',
                 'continuation_paragraphs':['Unchanged continuation.']}]},
            {'chapter':30,'section':2,'verses':[
                {'reference':'Proverbs 30:14','id':'p30-14','text':'Interleaved chapter body.'}]},
            {'chapter':24,'section':3,'verses':[
                {'reference':'Proverbs 24:23','id':'p24-23','text':'Later section body.'}]},
            {'chapter':30,'section':4,'verses':[
                {'reference':'Proverbs 30:15–16','id':'p30-15-16','text':'Composite original body.'}]}]}

    archive=ArchivedDanielTests.archive

    def test_authenticated_interleaved_sections_preserve_units_and_cross_section_range(self):
        edge,path=self.archive()
        edge['target']='Proverbs 24:22e-23'
        raw=path.read_bytes()
        chapters,units=validate.archived_target_book(edge,'Proverbs',{})
        expected=[v for c in self.document['chapters'] for v in c['verses']]
        self.assertEqual(list(units),[v['reference'] for v in expected])
        self.assertEqual(list(units.values()),expected)
        self.assertEqual(chapters['24'],['Proverbs 24:22e','Proverbs 24:22f','Proverbs 24:23'])
        self.assertEqual(chapters['30'],['Proverbs 30:14','Proverbs 30:15–16'])
        self.assertEqual(validate.ordered_range(chapters['24'],'Proverbs 24:22e','Proverbs 24:23'),chapters['24'])
        self.assertEqual(validate.complete_text(units['Proverbs 24:22f']),'Lettered original body.\nUnchanged continuation.')
        self.assertEqual(path.read_bytes(),raw)
        with self.assertRaisesRegex(ValueError,'Reversed target range'):
            validate.ordered_range(chapters['24'],'Proverbs 24:23','Proverbs 24:22e')

    def test_repeated_chapters_require_valid_distinct_explicit_sections(self):
        for index,field,value in [(2,'section',1),(1,'section',1),(2,'section',True),
                                  (2,'section',0),(2,'section',-1),(2,'section','3'),
                                  (2,'section',None),(2,'verses',{})]:
            with self.subTest(index=index,field=field,value=value):
                document=copy.deepcopy(self.document)
                document['chapters'][index][field]=value
                edge,_=self.archive(document)
                with self.assertRaisesRegex(ValueError,'section|chapters'):
                    validate.archived_target_book(edge,'Proverbs',{})
        for index in [0,2]:
            with self.subTest(missing_section=index):
                document=copy.deepcopy(self.document)
                del document['chapters'][index]['section']
                edge,_=self.archive(document)
                with self.assertRaisesRegex(ValueError,'distinct explicit sections'):
                    validate.archived_target_book(edge,'Proverbs',{})

    def test_overlapping_units_and_wrong_logical_chapter_are_rejected(self):
        for reference in ['Proverbs 24:22e','Proverbs 30:99']:
            with self.subTest(reference=reference):
                document=copy.deepcopy(self.document)
                document['chapters'][2]['verses'][0]['reference']=reference
                edge,_=self.archive(document)
                with self.assertRaisesRegex(ValueError,'unit reference'):
                    validate.archived_target_book(edge,'Proverbs',{})

    def test_repeated_sections_do_not_bypass_archive_hash_checks(self):
        edge,path=self.archive()
        path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'SHA256 mismatch'):
            validate.archived_target_book(edge,'Proverbs',{})
        edge,_=self.archive()
        edge['target_source']['blob_sha']='b'*40
        with self.assertRaisesRegex(ValueError,'Pinned target blob differs'):
            validate.archived_target_book(edge,'Proverbs',{})

    def test_unique_sections_preserve_original_non_numeric_labels(self):
        document={'book':'Sirach','chapters':[
            {'chapter':0,'section':1,'verses':[
                {'reference':'Sirach Prologue','id':'sirach-prologue','text':'Original prologue.'}]},
            {'chapter':1,'section':2,'verses':[
                {'reference':'Sirach 1:1','id':'sirach-1-1','text':'Original first chapter.'}]}]}
        edge,_=self.archive(document)
        chapters,units=validate.archived_target_book(edge,'Sirach',{})
        self.assertEqual(chapters['0'],['Sirach Prologue'])
        self.assertEqual(list(units.values()),[v for c in document['chapters'] for v in c['verses']])


class SavedCompositeTargetTests(unittest.TestCase):
    def test_esther_composite_targets_keep_their_declared_book(self):
        path=validate.ROOT/'esther'/'verses.json'
        original=path.read_bytes()
        document=json.loads(original)
        labels={'Esther 5:1–1c','Esther 5:1d–1f; 5:2'}
        units=[v for ch in document['chapters'] for v in ch['verses']]
        targets={e['target'] for v in units for e in v['cross_references']}
        self.assertTrue(labels<=targets)
        self.assertEqual(sum(len(v.get('continuation_paragraphs',[]))
                             for v in units if v['reference'] in labels),6)
        with patch('builtins.print'):
            reports=validate.validate(write_receipts=False)
        report=next(r for r in reports if r['book']=='Esther')
        self.assertEqual(report['target_book_membership'],'passed')
        self.assertEqual(report['complete_source_and_target_continuation_bodies'],'passed')
        self.assertEqual(path.read_bytes(),original)




class ClosedSourceUnitTests(unittest.TestCase):
    """Closed units are finished with a recorded reason and earn no completion credit."""
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.root_patch=patch.object(validate,'ROOT',self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.data={'book':'Ruth','chapters':[{'chapter':1,'status':'completed','verses':[
            {'reference':'Ruth 1:1','id':'v1-1','text':'A','status':'completed','cross_references':[{'id':'x'}]},
            {'reference':'Ruth 1:2','id':'v1-2','text':'B','status':'closed','cross_references':[],'closure_reason':'Bare name.','reviewed':'2026-11-01'}]}]}
        self.checks={'deferred_source_units':[],'closed_source_units':[
            {'source_reference':'Ruth 1:2','reason':'Bare name.','completed_source_credit':0,'completed_pair_credit':0}]}

    def write(self):
        folder=self.root/'ruth';folder.mkdir(exist_ok=True)
        (folder/'verses.json').write_text(json.dumps(self.data),encoding='utf-8')
        (folder/'source-checks.json').write_text(json.dumps(self.checks),encoding='utf-8')
        return {'books':[{'book':'Ruth','records':'ruth/'}],'next_unreviewed':None}

    def test_closed_unit_counts_as_finished_chapter(self):
        from chapter_structure import completed_chapter_numbers
        self.assertEqual(completed_chapter_numbers(self.data),[1])

    def test_closed_unit_is_not_a_continuation(self):
        self.assertIsNone(validate.validate_source_review_continuation(self.write()))

    def test_closed_unit_must_be_recorded_in_source_checks(self):
        self.checks['closed_source_units']=[]
        with self.assertRaisesRegex(ValueError,'Closed source units differ'):
            validate.validate_source_review_continuation(self.write())

    def test_closed_unit_cannot_earn_credit(self):
        self.checks['closed_source_units'][0]['completed_source_credit']=1
        with self.assertRaisesRegex(ValueError,'earns credit'):
            validate.validate_source_review_continuation(self.write())


if __name__=='__main__':
    unittest.main()
