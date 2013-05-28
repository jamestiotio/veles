#!/usr/bin/python
# encoding: utf-8
'''
This script extracts music features from audio files.

This script scans the given directories for files with the specified name
pattern and extracts the features from the configuration file, saving
the results to XML file.

It uses libSoundFeatureExtraction as the calculation backend.

@author:     Markovtsev Vadim

@copyright:  2013 Samsung R&D Institute Russia. All rights reserved.

@license:    Samsung Proprietary License

@contact:    v.markovtsev@samsung.com
@deffield    updated: 23.05.2013
'''

from itertools import chain
import logging
import multiprocessing as mp
import re
import sys
import os
from snd_features import SoundFeatures
from snd_file_loader import SndFileLoader
from sound_feature_extraction.library import Library

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

__all__ = []
__version__ = 1.0
__date__ = '2013-05-22'
__updated__ = '2013-05-23'


class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg

    def __str__(self):
        return self.msg

    def __unicode__(self):
        return self.msg


def mp_run(files, extr):
    logging.debug("Reading the files...")
    loader = SndFileLoader()
    loader.files_list = files
    loader.initialize()
    logging.debug("Decoding the files...")
    loader.run()

    extr.inputs = loader.outputs
    logging.debug("Extracting features...")
    extr.run()
    return extr.outputs


def filter_files(files, root, prefix, inpat, expat):
    for file in files:
        if (not inpat or \
                re.match(inpat, prefix + file)) and \
           (not expat or \
                not re.match(expat, prefix + file)):
            full_name = os.path.join(root, file)
            logging.debug("Added " + full_name)
            yield full_name


def main(argv=None):  # IGNORE:C0111
    '''Command line options.'''

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = \
        '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]
    program_license = '''%s

  Copyright 2013 Samsung R&D Institute Russia. All rights reserved.

  Licensed under Samsung Proprietary License

USAGE
''' % (program_shortdesc)
# -o /tmp/result.xml /home/markhor/Development/GTZAN
    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license,
                                formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-l", "--lib", dest="library",
                            default="libSoundFeatureExtraction.so",
                            help="path to the native library "
                                 "[default: %(default)s]",
                            metavar="path")
        parser.add_argument("-f", "--features", dest="features",
                            help="name of the file with feature "
                                 "descriptions [default: %(default)s]",
                            metavar="path", required=True)
        parser.add_argument("-o", "--output", dest="output",
                            help="name of the XML file with extracted "
                                 "features [default: %(default)s]",
                            metavar="path", required=True)
        parser.add_argument("-r", "--recursive", dest="recurse",
                            action="store_true", default=True,
                            help="recurse into subfolders [default: "
                                "%(default)s]")
        parser.add_argument("-v", "--verbose", dest="verbose",
                            action="count", default=0,
                            help="set verbosity level [default: %(default)s]")
        parser.add_argument("-i", "--include", dest="include",
                            help="only include paths matching this regex "
                                 "pattern. Note: exclude is given preference "
                                 "over include. [default: %(default)s]",
                                 metavar="RE")
        parser.add_argument("-e", "--exclude", dest="exclude",
                            help="exclude paths matching this regex pattern. "
                                 "[default: %(default)s]", metavar="RE")
        parser.add_argument('-V', '--version', action='version',
                            version=program_version_message)
        parser.add_argument(dest="paths",
                            help="paths to folder(s) with audio file(s) "
                                 "[default: %(default)s]",
                            metavar="path", nargs='+')

        # Process arguments
        args = parser.parse_args()

        library_path = args.library
        feature_file = args.features
        output = args.output
        paths = args.paths
        verbose = args.verbose
        recurse = args.recurse
        inpat = args.include
        expat = args.exclude

        if verbose > 4:
            verbose = 4
        logging.basicConfig(level=50 - verbose * 10)

        if inpat and expat and inpat == expat:
            raise CLIError("include and exclude pattern are equal! "
                           "Nothing will be processed.")

        # We can do work in parallel more effectively with multiprocessing
        Library(library_path).set_omp_transforms_max_threads_num(1)

        features = open(feature_file).read().split(";")
        features.remove("")
        logging.info("Read %d features" % len(features))

        found_files = []
        for inpath in paths:
            if recurse:
                for root, dirs, files in os.walk(inpath, followlinks=True):
                    logging.debug("Scanning " + root + "...")
                    found_files.extend(filter_files(files, root,
                                                    root[len(inpath):],
                                                    inpat, expat))
            else:
                files = [f for f in os.listdir(inpath) \
                         if os.path.isfile(os.path.join(inpath, f))]
                found_files.extend(filter_files(files, root,
                                                "", inpat, expat))

        if len(found_files) == 0:
            logging.warn("No files were found")
            return 0
        logging.info("Found %d files" % len(found_files))
        extr = SoundFeatures()
        logging.debug("Parsing the supplied features...")
        extr.add_features(features)
        extr.initialize()

        pcount = mp.cpu_count()
        splitted_found_files = [found_files[i::pcount] for i in range(pcount)]
        with mp.Pool(pcount) as pool:
            results_async = [pool.apply_async(
                                mp_run, (splitted_found_files[i], extr,)) \
                             for i in range(0, pcount)]
            pool.close()
            pool.join()
            extr.outputs = list(chain(*[r.get() for r in results_async]))

        logging.debug("Saving the results...")
        extr.save_to_file(output, list(chain(*splitted_found_files)))

        logging.debug("Done")
        return 0
    except KeyboardInterrupt:
        logging.critical("Interrupted")
        return 0
    except Exception as e:
        # logging.critical(program_name + ": " + repr(e) + ":")
        raise
        return 2

if __name__ == "__main__":
    sys.exit(main())
