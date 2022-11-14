# Documentation: https://github.com/Homebrew/homebrew/blob/master/share/doc/homebrew/Formula-Cookbook.md
#                /usr/local/Library/Contributions/example-formula.rb
# PLEASE REMOVE ALL GENERATED COMMENTS BEFORE SUBMITTING YOUR PULL REQUEST!

class BeardedAvenger < Formula
  homepage "https://csirtgadgets.org/collective-intelligence-framework"
  url "https://github.com/csirtgadgets/bearded-avenger/archive/master.zip"
  sha256 ""

  head "https://github.com/csirtgadgets/bearded-avenger.git", :branch => "master"
  depends_on "libyaml"

  # depends_on "cmake" => :build
  resource "pyzmq" do
      url "https://pypi.python.org/packages/source/p/pyzmq/pyzmq-14.7.0.tar.gz"
      sha256 "77994f80360488e7153e64e5959dc5471531d1648e3a4bff14a714d074a38cc2"
  end

  def install
    # ENV.deparallelize  # if your formula fails when building in parallel
    cd "source/python" do
      system "python", *Language::Python.setup_install_args(prefix)
    end
  end

  test do
    # `test do` will create, run in and delete a temporary directory.
    #
    # This test will fail and we won't accept that! It's enough to just replace
    # "false" with the main program this formula installs, but it'd be nice if you
    # were more thorough. Run the test with `brew test bearded-avenger`. Options passed
    # to `brew install` such as `--HEAD` also need to be provided to `brew test`.
    #
    # The installed folder is not in the path, so use the entire path to any
    # executables being tested: `system "#{bin}/program", "do", "something"`.
    system "pytest"
  end
end
