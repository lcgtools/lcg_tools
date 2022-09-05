# lcgtools

lcgtools includes custom card convenience tools for
[living card games](https://tinyurl.com/4svyjmpj).

- `lcg_pdf` generates PDF files for printing cards, either folded prints (fold
  along fold line and glue sides together) or 2-sided printing. It adds
  bleed to card images and can automatically rotate images to portrait aspect.

- `lcg_cardlist` generates card lists for `lcg_pdf`. It allows feeding multiple
  sets of card into one PDF generation job, including all cards in one single
  PDF document and reducing paper waste.

- `lcg_image` includes some convenience card image transformation which includes
  image rotation (to desired aspect mode), setting physical dimensions, and
  adding bleed or cropping excess bleed.

# License

lcgtools is released under the [GNU Lesser General Public License
v3.0](https://www.gnu.org/licenses/lgpl-3.0-standalone.html) or later. License
details are included with the source code.

# Alpha software

The package is an alpha release and is still in development. Though we strive
to make each release functional, some things may not work as expected. As
the tools are in development, tool usage and APIs may undergo changes between
releases.

# Installing

The library with source code can be installed from
[PyPI](https://pypi.org/project/lcgtools/). Dependencies include:

- [PySide6](https://pypi.org/project/PySide6/) Qt bindings for python (see the
  [reference](https://doc.qt.io/qtforpython/index.html) for more info)

- [setuptools](https://pypi.org/project/setuptools/) for building from source

The package has been tested to work on OSX, Linux, and Windows (tested with
python from [Microsoft Store](https://tinyurl.com/ekz5558m) and
[Anaconda](https://anaconda.org/)). Unfortunately, it does not (currently) work
with Windows Subsystem for Linux (WSL) due to lack of PySide6 support.

lcgtools can be installed from PyPI with the command

```bash
pip install lcgtools  # Alternatively python3 -m pip install lcgtools
````

To install lcgtools from source, run this command from the top directory
(which includes the `pyproject.toml` file),

```bash
pip install .    # alternatively "python -m pip install ."
```

You may wish to install lcgtools with [virtualenv](https://tinyurl.com/2p8hux4r)
in order to separate the install from your general python environment.

# Usage

## Simple lcg_pdf Usage

Assuming input cards include no bleed, the following command creates a pdf
with all cards in the hero_cards subdirectory.

```bash
lcg_pdf --verbose --output out.pdf --back back/player.png hero_deck/*
```

If the back side image includes 3 mm bleed, the command instead becomes.

```bash
lcg_pdf --verbose --output out.pdf --back back/player.png --back_bleed 3 hero_deck/*
```

We could include card front images by specifying directories rather than
individual files. This is useful on Windows with its limited shell capabilities
(i.e. lack of command line wildcards). When a directory is listed, all images
in that directory are included.

```bash
lcg_pdf --verbose --output out.pdf --back back/player.png --back_bleed 3 hero_deck/
```

Bleed is automatically added to output images as per defaults set in the program
or config files. We can override this with the `--bleed` parameter. The
following command generates output with 1 mm bleed on card front and back sides,
adding bleed (or cropping excess bleed) as necessary.

```bash
lcg_pdf --verbose --output out.pdf --bleed 1 --back back/player.png hero_deck/*
```

The default output of `lcg_pdf` is a PDF document with A4 page format for fold
printing, however the program also supports 2-sided printing and other
page formats. The following command generates a 2-sided US Letter document.

```bash
lcg_pdf --verbose --output out.pdf --pagesize=letter --twosided --back back/player.png hero_deck/*
```

## Using config files

It is possible to use a config file to override default values for many of the
command line parameters. The `--game` argument is used as the filename of the
config file (followed by the `.ini` extension) , allowing different config
files for different card games.

Additionally, some parameters can be set for individual *profiles*. The profile
to apply for a configuration file is passed to `lcg_pdf` as a `--profile`
argument. Currently profiles are used to set different default back side images
for different card types.

If we supply a `--conf` argument, a config file is read from the expected
location of that file. If the file is not found, the program generates an error
message which shows the path to the missing file, e.g.

```bash
lcg_pdf --conf --output /tmp/dummy_arg
```

The config file follows the basic INI file format of python's
[configparser](https://docs.python.org/3/library/configparser.html) module. The
name of the config file is either `lcg_pdf.ini` (the default configuration
file), or `[game].ini`. The location for the config file is either
`~/Library/Application\ Support/lcg_pdf/` (OSX), `~/.config/lcg_pdf/` (Linux) or
`%userprofile%\appdata\Local\Cloudberries\lcg_pdf\` (Windows).

Below is a config file `mc.ini` for a `--game mc` argument to `lcg_pdf`
which includes profiles for "player", "encounter" and "villain" cards. Each
profile defines a default card background image which already includes 3 mm
bleed.

```
[default]
pagesize = A4
page_dpi = 600
card_width_mm = 63.5
card_height_mm = 88
card_bleed_mm = 3

[player]
backside_image_file = ~/cards/mcg/player.png
backside_bleed_mm = 3

[encounter]
backside_image_file = ~/cards/mcg/encounter.png
backside_bleed_mm = 3

[villain]
backside_image_file = ~/cards/mcg/villain.png
backside_bleed_mm = 3
```

With this config file, the following command will automatically apply the
*player* profile card background to the output cards PDF.

```bash
lcg_pdf --verbose --conf --game mc --output out.pdf --profile player hero_deck/*
```

lcgtools includes an example INI file which shows all configurable options with
a short description.

## Combining multiple card sets

When we pass card images to `lcg_pdf`, all cards are generated with the same
back side. If we instead wish to create a PDF document which includes different
card types, we can do so by preparing a *card list* for `lcg_pdf` with
the tool `lcg_cardlist`. For the average user, it will probably be most
convenient and/or practical to write card lists to a file. Such lists can
however be written to stdout and can be chained between multiple uses of the
command, piping the final result directly into `lcg_pdf`.

The following set of commands generate card lists for a special "hero card", a
set of "player" cards, and a set of "encounter" cards. We use the `--conf`
mechanism to use defined default back sides of cards as described above. Note
the use of the `--append` option when adding cards to an already existing list.

```bash
lcg_cardlist --verbose --conf --game mc --output CARDS.TXT --back hero_card/back.png hero_card/front.png
lcg_cardlist --verbose --conf --game mc --output CARDS.TXT --append --profile player hero_deck/*
lcg_cardlist --verbose --conf --game mc --output CARDS.TXT --append --profile encounter nemesis/*
```

The generated cards list can be used as an input to `lcg_pdf`, which loads the
appropriate back side images and applies the relevant card bleed information
defined for each card set, e.g.

```bash
lcg_pdf --verbose --conf --game mc --output out.pdf --list CARDS.TXT
```

## Simple image conversions

The tool `lcg_image` supports some image transformation which can be useful when
working with custom cards. It takes some of the transformations that were
developed for `lcg_pdf` and enables applying them to single images or sets of
images. This could be useful for working together with other card printing
tools, e.g. using `lcg_image` to rotate cards to portrait mode before feeding
them to another PDF generation program. The following example sets the
physical size of an image, adds 5 mm bleed, and rotates images with a landscape
aspect to a portrait aspect.

```bash
lcg_image --output converted.png --to_portrait --resize --width 63.5 --height 88 --bleed 5 player.png
```

The following command will perform the same transformation on each specified
input image, writing results to images with `converted_` as an added filename
prefix.

```bash
lcg_image --prefix converted_ --to_portrait --resize --width 63.5 --height 88 --bleed 5 *.png
```

# Other information

When printing PDF documents generated with `lcg_pdf`, make sure to set up
printing so that it **prints to actual size** for the document. Many PDF viewers
are set up by default to print documents scaled to print all content, including
page margins. This leads to cards being scaled to a smaller size than their
intended specified physical size.

# What to expect going forward

To discuss where we are going with this tool, I'll make a couple comments about
where it started. It all began with some friends introducing me to
[Marvel Champions: The Card Game](https://tinyurl.com/y5pbhcua). One thing led
to the other, and a couple months later I am the proud owner of pretty much all
the cards which have been released, having fun getting into the game. During my
various browsing I came across the wonderful world of custom game content;
a Google Search for "marvel champions custom" will take you to the
[Hall of Heroes](https://hallofheroeslcg.com/custom-content/) web site, and
eventually you end up on the Marvel Champions LCG Homebrew
[discord](https://discordapp.com/invite/fWrvrNh) with nice people and lots of
custom content.

As I played around with how to print sets, I ended up wanting to make my own
thing because "why not" and "putting stuff on PDFs from scripts can't be that
hard, can it?", and then I could make the tool the way I wanted to, plus
I wanted it to be multi platform.

I started out with a dirty hard-coded hack, improved it a bit, added a command
line interface, tried to modify it so that others might be able to use it and
understand how it works, made it packageable for PyPI, etc. What started out as
an "evening hack" turned out to be a bit more work. However, this unfortunately
means I don't currently get to *play* the game as I am too busy developing this
thing. So now that the tool seems to be in a reasonable shape as an initial
release that I can share it without hopefully being too embarrassed, I
want to get it published so I can get back to playing the game and *using* the
tool.

With regards to the future; this is not my day job, it is a small side
project in the midst of a very busy family life with small kids, plus I am not
a developer by trade, so you should probably not expect an active maintainer who
immediately jumps on every issue. That being said, I do hate it when stuff does
not work as intended, so I'll probably want to try to sort things out if there
are issues.
