# Kirei

**Kirei** (綺麗 jap. *pretty, clean, tidy*) is a basic open-source
[osu!](http://osu.ppy.sh) skin, built from the ground up using
[Inkscape](http://inkscape.org).

Its main goal is to serve as an open, customizable starting point for further
modifications, without adding unnescessary visual noise. Its heavy use of SVG
embedding makes changing existing elements easy.

### [Download](/releases/latest) <small>([all releases](/releases))</small>

![Preview](preview.png "Kirei")

## Building

Dependencies:
- [Python 3](https://python.org/)
- [GNU make](https://www.gnu.org/software/make/)
  ([Windows build](http://www.equation.com/servlet/equation.cmd?fa=make))
- A supported SVG rasterizer:
  - [ImageMagick](https://www.imagemagick.org/script/binary-releases.php)
  (recommended)
  - `rsvg-convert` from [libRSVG](https://wiki.gnome.org/action/show/Projects/LibRsvg)
  ([Windows build](http://opensourcepack.blogspot.com/2012/06/rsvg-convert-svg-image-conversion-tool.html))
  - [Inkscape](https://inkscape.org/en/download/) (unreliable and slow)


- Make sure `make` and `python` are in your `PATH`.
  - Windows: Just drop `make.exe` into the Kirei folder if you want.
- Run `python3 generator.py`.
  - If the script doesn't find your rasterizer, try adding it to your `PATH` too.
  - This should be re-ran after a file has been added or removed from the source
    folder or dependency links between files modified.
- Run `make all`.
- Zip up the `build` folder (the files must be at the root) and rename the
  archive to end in `.osk`.
  - E.g. `zip -r build kirei.osk`

## Contributing

Contributions to this project are highly encouraged. Feel free to fork it to
make your own modifications and submit relevant pull-requests to `develop` or
their own feature branches.

If git seems too intimidating to you, you can also create a new issue
and attach modified files to it.

### Releasing

This project follows a simplified variant of Vincent Driessen's
[branching model](http://nvie.com/posts/a-successful-git-branching-model/)
(without hotfixes, release branches are kept local and closed immediately)
and [Semantic Versioning](http://semver.io).

- Branch out `release-MAJOR.MINOR.PATCH` from `master`
  (i.e. `git flow release start`).
- Bump the version numbers inside `skin.ini` and do other last-minute changes.
- Build `kirei-MAJOR.MINOR.PATCH.osk` as described above, but run `make release`
  instead of `make all`.
- Finish the release branch, tag it, merge it back into `develop` and `master`
  and push it (i.e. `git flow release finish --push`).
- Draft a new release on GitHub using the newly created tag (@ master). Upload
  the OSK file as a binary and publish it.
