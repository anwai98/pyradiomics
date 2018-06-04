import logging
import os
import sys

import numpy
import six

from radiomics import generalinfo, getFeatureClasses
from testUtils import PyRadiomicsBaseline, RadiomicsTestUtils


class AddBaseline:

  def __init__(self):
    self.logger = logging.getLogger('radiomics.addBaseline')

    self.testUtils = RadiomicsTestUtils()

    self.testCases = sorted(self.testUtils.getTests())
    self.featureClasses = getFeatureClasses()

    dataDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    self.baselineDir = os.path.join(dataDir, "baseline")

  def generate_scenarios(self):
    for test in self.testCases:
      for className, featureClass in six.iteritems(self.featureClasses):
        if not os.path.exists(os.path.join(self.baselineDir, 'baseline_%s.csv' % (className))):
          self.logger.debug('generate_scenarios: featureClass = %s', className)
          yield test, className

  def process_testcase(self, test, featureClassName):
    self.logger.debug('processing testCase = %s, featureClassName = %s', test, featureClassName)

    self.testUtils.setFeatureClassAndTestCase(featureClassName, test)

    testImage = self.testUtils.getImage('original')
    testMask = self.testUtils.getMask('original')

    featureClass = self.featureClasses[featureClassName](testImage, testMask, **self.testUtils.getSettings())

    if "_calculateCMatrix" in dir(featureClass):
      cMat = getattr(featureClass, 'P_%s' % featureClassName)
      if cMat is not None:
        numpy.save(os.path.join(self.baselineDir, '%s_%s.npy' % (test, featureClassName)), cMat)

    featureClass.enableAllFeatures()
    featureClass.calculateFeatures()

    imageTypeName = 'original'

    # Update versions to reflect which configuration generated the baseline
    versions = {}
    versions['general_info_Version'] = generalinfo.GeneralInfo.getVersionValue()
    versions['general_info_NumpyVersion'] = generalinfo.GeneralInfo.getNumpyVersionValue()
    versions['general_info_SimpleITKVersion'] = generalinfo.GeneralInfo.getSimpleITKVersionValue()
    versions['general_info_PyWaveletVersion'] = generalinfo.GeneralInfo.getPyWaveletVersionValue()
    self.new_baselines[featureClassName].configuration[test].update(versions)

    self.new_baselines[featureClassName].baseline[test] = {'%s_%s_%s' % (imageTypeName, featureClassName, key): val
                                                           for key, val in six.iteritems(featureClass.featureValues)}

  def run(self, featureClass=None):
    current_baseline = self.testUtils._baseline
    config = current_baseline[current_baseline.keys()[0]].configuration
    self.new_baselines = {}
    if featureClass is None:
      for test, newClass in self.generate_scenarios():
        if newClass not in self.new_baselines:
          self.logger.info('Adding class %s to the baseline', newClass)
          self.new_baselines[newClass] = PyRadiomicsBaseline(newClass)
          self.new_baselines[newClass].config = config
          # add the new baseline to test utils so it's config can be used during processing
          self.testUtils._baseline[newClass] = self.new_baselines[newClass]

        self.process_testcase(test, newClass)

      for newClass in self.new_baselines:
        self.new_baselines[newClass].writeBaselineFile(self.baselineDir)
    elif featureClass in self.featureClasses:
      if featureClass in current_baseline:
        # Re-create the baseline for specified class
        self.new_baselines[featureClass] = current_baseline[featureClass]
      else:
        # Feature class not yet present in the baseline, generate a new one
        self.new_baselines[featureClass] = PyRadiomicsBaseline(featureClass)
        self.new_baselines[featureClass].config = config

      for test in self.testCases:
        self.process_testcase(test, featureClass)

      self.new_baselines[featureClass].writeBaselineFile(self.baselineDir)
    else:
      self.logger.error('Feature Class %s not recognized, cannot create baseline!', featureClass)


if __name__ == '__main__':
  add_baseline = AddBaseline()
  if len(sys.argv) == 2:
    add_baseline.run(sys.argv[1])
  else:
    add_baseline.run()