# Contributing
[ [Read Me](README.md) &middot; [Todo](../../issues?q=is%3Aopen+is%3Aissue+sort%3Acreated-asc) &middot; [Design](DESIGN.md) &middot; [Contributing](CONTRIBUTING.md)]

Implementing the whole set of skin elements is a big task, especially if you
don't have a clue about graphic design like me, so contributions to this project
are highly encouraged. Forks should be made off the `develop` branch.

If git seems too intimidating to you, you can also create a new issue
and attach modified files to it.

## Building

Due to the large number of SVG files and changes of a single graphic that is
included in other files causing them to inherit the change and needing to be re-
rasterized, a decision has been made to automate the rasterizing process.

The generator script will scan the source directory for SVG files, collect all
dependencies of them and generate a Makefile that will automatically rasterize
only the SVG files that have been affected by changes.

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
- Run `make package`.
- Double-click the finished OSK file to install the skin.

## Releasing

This project follows a simplified variant of Vincent Driessen's
[branching model](http://nvie.com/posts/a-successful-git-branching-model/)
(without hotfixes, release branches are kept local and closed immediately)
and [Semantic Versioning](http://semver.io).

- Branch out `release-MAJOR.MINOR.PATCH` from `master`
  (i.e. `git flow release start`).
- Bump the version numbers inside `skin.ini` and do other last-minute changes.
- Build `Kirei-MAJOR.MINOR.PATCH.osk` as described above.
- Finish the release branch, tag it, merge it back into `develop` and `master`
  and push it (i.e. `git flow release finish --push`).
- Draft a new release on GitHub using the newly created tag (@ master). Upload
  the OSK file as a binary and publish it.
