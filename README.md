## What is rivulet.audio?

rivulet.audio is a new way to acquire and organize music. You create a playlist of songs and it automatically finds "sources" by searching for those songs in torrents. You can share these playlists with anyone and publish them anywhere because the don't contain any copyrighted content or any information about where to get the songs. Once the other user imports your playlist, their client will find torrents to play the songs from.

## OS X Installation

1. Open Terminal.app

2. Install homebrew

  ```
  ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
  ```

3. Install rivulet from our own tap (Note: We need to have a repo called `homebrew-tap`, and have `rivulet.rb` in it)

  ```
  brew install rivuletaudio/tap/rivulet
  ```

4. `rivulet` should be ready to use in terminal

# Debian/Ubuntu Installation

```
git clone https://github.com/rivuletaudio/rivulet.git
sudo apt-get install python-libtorrent
sudo apt-get install flac
sudo apt-get install lame
sudo pip2 install BeautifulSoup4
sudo pip2 install tornado
sudo pip2 install lxml
sudo pip2 install pyyaml
```

# Arch linux installation

```
yaourt rivulet
```

# Running

You can run rivulet.audio on your private server or locally.

```
rivulet
```

or


```
python2 server/webserver/webserver.py
```

then visit `http://localhost:3000` in your browser.
