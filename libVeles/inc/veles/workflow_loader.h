/*! @file workflow_loader.h
 *  @brief Declaration of WorkflowLoader class.
 *  @author Vadim Markovtsev <v.markovtsev@samsung.com>, Bulychev Egor <e.bulychev@samsung.com>
 *  @version 1.0
 *
 *  @section Notes
 *  This code partially conforms to <a href="http://google-styleguide.googlecode.com/svn/trunk/cppguide.xml">Google C++ Style Guide</a>.
 *
 *  @section Copyright
 *  Copyright 2013 Samsung R&D Institute Russia
 */

#ifndef INC_VELES_WORKFLOW_LOADER_H_
#define INC_VELES_WORKFLOW_LOADER_H_
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

#include <veles/logger.h>  // NOLINT(*)
#include <veles/workflow.h>  // NOLINT(*)
#include <veles/poison.h>  // NOLINT(*)

#if __GNUC__ >= 4
#pragma GCC visibility push(default)
#endif

namespace veles {

class WorkflowLoadingFailedException : public std::exception {
 public:
  WorkflowLoadingFailedException(const std::string& file,
                                 const std::string& reason)
      : message_(std::string("Extraction of the workflow \"") + file +
                 "\" has failed due to " + reason + ".") {
  }

  virtual const char* what() const noexcept {
    return message_.c_str();
  }

 private:
  std::string message_;
};

/**
 * @brief Factory which produces Workflow objects from packages stored on disk.
 * */
class WorkflowLoader : protected DefaultLogger<WorkflowLoader,
                                               Logger::COLOR_YELLOW> {
 public:
  friend class WorkflowLoaderTest;
  WorkflowLoader();
  virtual ~WorkflowLoader() = default;
  /// @brief Main function.
  /**
   * @param[in] archive Path to the package.
   * @return The loaded and ready to be initialized Workflow instance.
   *
   * 1) Extract archive (using libarchive) to directory kWorkDirectory.\n
   * 2) Read WorkflowDescription from kWorkflowDecompressedFile\n
   * 3) Go through workflow units, reading properties and dereferencing binary\n
   * references.\n
   * 4) Construct the workflow from links tree.\n
   * 5) Delete kWorkDirectory with all files.
   */
  Workflow Load(const std::string& archive);

 private:
  struct WorkflowArchive {
    std::string main;
    std::unordered_map<std::string, void*> arrays;
  };

  WorkflowArchive ExtractArchive(const std::string& filename);

   /// Name of the file which describes the workflow.
  static const char* kMainFile;
};

}  // namespace Veles

#if __GNUC__ >= 4
#pragma GCC visibility pop
#endif

#endif  // INC_VELES_WORKFLOW_LOADER_H_
