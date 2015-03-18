class Rivulet < Formula
  homepage "http://rivulet.audio/"
  url "file:///Users/rz/dev/wwp-sandbox/rivulet.tar.gz"
  version "0.1"
  sha256 "461781243d3a1c6be44b604ea79cecffdf39f4b724ecf8023c9cc9dc1a426743"

  # depends_on "cmake" => :build
  depends_on :python
  depends_on "boost-python"
  depends_on "libtorrent-rasterbar" => "--with-python"
  depends_on "flac"
  depends_on "lame"
             
  def install

    # install python dependencies into brew installed python
    system "pip2", "install", "--install-option=--prefix=#{HOMEBREW_PREFIX}", "beautifulsoup4"
    system "pip2", "install", "--install-option=--prefix=#{HOMEBREW_PREFIX}", "mock"
    system "pip2", "install", "--install-option=--prefix=#{HOMEBREW_PREFIX}", "tornado>=4.1"
    system "pip2", "install", "--install-option=--prefix=#{HOMEBREW_PREFIX}", "lxml"
    system "pip2", "install", "--install-option=--prefix=#{HOMEBREW_PREFIX}", "pyyaml"
    
    File.write("./run-osx.sh", "#!/bin/sh\nexport PATH=#{HOMEBREW_PREFIX}/bin:$PATH\nexec #{HOMEBREW_PREFIX}/bin/python2 #{prefix}/server/webserver/webserver.py")
    File.new("./run-osx.sh").chmod(0777)
    
    FileUtils.cp_r "./", "#{prefix}"
    
    if File.exist?("#{HOMEBREW_PREFIX}/bin/rivulet")
      File.unlink("#{HOMEBREW_PREFIX}/bin/rivulet")
    end
    
    File.link("#{prefix}/run-osx.sh", "#{HOMEBREW_PREFIX}/bin/rivulet")

    if File.exist?("/Applications/Rivulet.app")
      FileUtils.rmdir("/Applications/Rivulet.app")
    end
    
    FileUtils.cp_r("#{prefix}/osx-agent/Rivulet.app", "/Applications/Rivulet.app")
  end

  test do
    Language::Python.each_python(build) do |python, _version|
      system python, "-c", "import libtorrent; libtorrent.version"
    end
  end
end
