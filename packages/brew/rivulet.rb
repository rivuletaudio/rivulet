class Rivulet < Formula
  homepage "http://rivulet.audio/"
  url "file:///Users/rz/dev/wwp-sandbox/rivulet-0.1.tar.gz"
  version "0.1"
  sha256 "5bc00f68b30728e9146d52a28a980ba91a57ca34f13026e106c3887129e9cb6f"

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
    
    File.write("./run-osx.sh", "#!/bin/sh\npython2 #{prefix}/server/webserver/webserver.py")
    File.new("./run-osx.sh").chmod(0777)
    
    FileUtils.cp_r "./", "#{prefix}"
    
    if File.exist?("#{HOMEBREW_PREFIX}/bin/rivulet")
      File.unlink("#{HOMEBREW_PREFIX}/bin/rivulet")
    end
    
    File.link("#{prefix}/run-osx.sh", "#{HOMEBREW_PREFIX}/bin/rivulet")
  end

  test do
    Language::Python.each_python(build) do |python, _version|
      system python, "-c", "import libtorrent; libtorrent.version"
    end
  end
end
