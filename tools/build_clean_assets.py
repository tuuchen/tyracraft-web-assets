from pathlib import Path
import math
import json
import shutil

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "release-assets"
OUT = ROOT / "clean-assets"
GENERATED = ROOT / "generated-clean-assets"


def crop_cell(image: Image.Image, columns: int, rows: int, index: int, size: int) -> Image.Image:
    column, row = index % columns, index // columns
    x0 = round(column * image.width / columns)
    x1 = round((column + 1) * image.width / columns)
    y0 = round(row * image.height / rows)
    y1 = round((row + 1) * image.height / rows)
    inset = max(1, round(min(x1 - x0, y1 - y0) * 0.025))
    tile = image.crop((x0 + inset, y0 + inset, x1 - inset, y1 - inset))
    return tile.resize((size, size), Image.Resampling.LANCZOS)


def transparent_item(sheet: Image.Image, index: int, size: int = 32) -> Image.Image:
    tile = crop_cell(sheet, 7, 7, index, size).convert("RGBA")
    pixels = tile.load()
    for y in range(size):
        for x in range(size):
            red, green, blue, alpha = pixels[x, y]
            if alpha < 105 or (red + green + blue < 65 and alpha < 245):
                pixels[x, y] = (0, 0, 0, 0)
    return tile


def make_pattern(color: tuple[int, int, int]) -> Image.Image:
    tile = Image.new("RGBA", (16, 16), (*color, 255))
    draw = ImageDraw.Draw(tile)
    dark = tuple(max(0, value - 22) for value in color)
    light = tuple(min(255, value + 20) for value in color)
    for y in range(16):
        for x in range(16):
            if (x * 5 + y * 3) % 11 == 0:
                draw.point((x, y), fill=(*dark, 255))
            elif (x * 7 + y) % 13 == 0:
                draw.point((x, y), fill=(*light, 255))
    return tile


def make_block_atlas(block_sheet: Image.Image, item_sheet: Image.Image) -> Image.Image:
    atlas = Image.new("RGBA", (256, 256), (0, 0, 0, 0))

    # target TyraCraft atlas index -> source index in the generated 16x16 sheet
    mapping = {
        0: 0, 1: 16, 6: 16, 16: 2, 17: 19, 22: 20,
        80: 92, 96: 240, 97: 10, 98: 9, 99: 13,
        100: 144, 101: 103, 112: 244, 113: 101, 114: 96,
        115: 5, 116: 81, 128: 114, 129: 113, 130: 112,
        131: 115, 132: 117, 133: 116, 144: 176, 162: 38,
        163: 32, 176: 24, 177: 25, 178: 19, 179: 18,
        208: 200, 209: 200, 210: 201, 211: 200, 212: 189,
    }
    for target, source in mapping.items():
        tile = crop_cell(block_sheet, 16, 16, source, 16).convert("RGBA")
        atlas.alpha_composite(tile, ((target % 16) * 16, (target // 16) * 16))

    wool = {
        102: (226, 182, 55), 103: (48, 91, 184), 104: (83, 145, 65),
        105: (222, 122, 48), 106: (139, 65, 172), 107: (183, 53, 58),
        108: (223, 226, 216), 109: (39, 43, 50),
    }
    for target, color in wool.items():
        atlas.alpha_composite(make_pattern(color), ((target % 16) * 16, (target // 16) * 16))

    # Crossed vegetation needs transparent silhouettes; use generated item art.
    vegetation = {167: 36, 168: 37, 169: 35}
    for target, source in vegetation.items():
        tile = transparent_item(item_sheet, source, 16)
        atlas.alpha_composite(tile, ((target % 16) * 16, (target // 16) * 16))
    atlas.alpha_composite(transparent_item(item_sheet, 41, 16), (16, 0))
    return atlas


def make_items(sheet: Image.Image, output: Path) -> None:
    mapping = {
        "stone.png": 0, "mossy_stone_bricks.png": 1,
        "mossy_stone_bricks_slab.png": 15, "cracked_stone_bricks.png": 2,
        "cracked_stone_bricks_slab.png": 14, "chiseled_stone_bricks.png": 3,
        "stone_brick.png": 4, "stone_brick_slab.png": 18,
        "bricks.png": 5, "bricks_slab.png": 15,
        "oak_log.png": 7, "birch_log.png": 8,
        "stripped_oak_wood.png": 9, "acacia_planks.png": 10,
        "oak_planks.png": 11, "spruce_planks.png": 12, "birch_planks.png": 13,
        "stone_slab.png": 14, "oak_slab.png": 16, "spruce_slab.png": 17,
        "acacia_slab.png": 19, "birch_slab.png": 20,
        "red_wool.png": 21, "blue_wool.png": 22, "green_wool.png": 23,
        "yellow_wool.png": 24, "purple_wool.png": 25, "orange_wool.png": 26,
        "white_wool.png": 27, "black_wool.png": 20,
        "coal_ore_block.png": 28, "iron_ore_block.png": 29,
        "gold_ore_block.png": 30, "redstone_ore_block.png": 31,
        "emerald_ore_block.png": 32, "diamond_ore_block.png": 33,
        "glowstone.png": 34, "dandelion_flower.png": 35,
        "poppy_flower.png": 36, "pumpkin.png": 40,
        "jack_o_lantern.png": 40, "torch.png": 41, "glass.png": 42,
        "sand.png": 43, "dirt.png": 44, "gravel.png": 45,
        "water_bucket.png": 46, "lava_bucket.png": 47, "wooden_axe.png": 48,
    }
    output.mkdir(parents=True, exist_ok=True)
    for name, index in mapping.items():
        transparent_item(sheet, index).save(output / name, optimize=True)


def make_font(path: Path) -> None:
    cell = 32
    image = Image.new("RGBA", (cell * 16, cell * 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    for value in range(256):
        character = bytes([value]).decode("cp1252", errors="replace")
        box = draw.textbbox((0, 0), character, font=font)
        width, height = box[2] - box[0], box[3] - box[1]
        x = (value % 16) * cell + (cell - width) // 2 - box[0]
        y = (value // 16) * cell + (cell - height) // 2 - box[1]
        draw.text((x, y), character, font=font, fill=(244, 248, 240, 255))
    image.save(path, optimize=True)


def make_skin(path: Path, palette: tuple[tuple[int, int, int], ...]) -> None:
    skin = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(skin)
    face, hair, shirt, trousers, accent = palette
    rectangles = [
        (8, 8, 15, 15, face), (0, 8, 7, 15, face), (16, 8, 31, 15, hair),
        (20, 20, 27, 31, shirt), (16, 20, 19, 31, accent),
        (28, 20, 39, 31, shirt), (4, 20, 11, 31, trousers),
        (0, 20, 3, 31, accent), (12, 20, 15, 31, trousers),
        (44, 20, 47, 31, face), (40, 20, 43, 31, shirt),
        (48, 20, 55, 31, shirt),
    ]
    for x0, y0, x1, y1, color in rectangles:
        draw.rectangle((x0, y0, x1, y1), fill=(*color, 255))
    draw.rectangle((10, 11, 10, 11), fill=(28, 39, 48, 255))
    draw.rectangle((13, 11, 13, 11), fill=(28, 39, 48, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    skin.save(path, optimize=True)


def make_environment(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    clouds = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(clouds)
    for i in range(28):
        x, y = (i * 73) % 256, (i * 41) % 256
        draw.rectangle((x, y, min(255, x + 18 + i % 17), min(255, y + 5)), fill=(236, 244, 238, 190))
    clouds.save(output / "clouds.png", optimize=True)
    Image.new("RGBA", (16, 16), (185, 205, 201, 115)).save(output / "fog.png", optimize=True)
    for name, color, ring in [
        ("sun.png", (255, 198, 77, 255), (255, 235, 164, 255)),
        ("moon.png", (186, 220, 225, 255), (98, 146, 165, 255)),
    ]:
        icon = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        icon_draw = ImageDraw.Draw(icon)
        icon_draw.ellipse((4, 4, 27, 27), fill=color, outline=ring, width=3)
        icon.save(output / name, optimize=True)


if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(SOURCE, OUT)
shutil.rmtree(OUT / "textures" / "texture_packs" / "mine4k", ignore_errors=True)

block_sheet = Image.open(GENERATED / "original-block-atlas-source.png")
item_sheet = Image.open(GENERATED / "original-item-sheet-source.png")
atlas = make_block_atlas(block_sheet, item_sheet)
block_dir = OUT / "textures" / "texture_packs" / "default" / "block"
atlas.save(block_dir / "texture_atlas.png", optimize=True)
atlas.resize((128, 128), Image.Resampling.NEAREST).save(block_dir / "texture_atlas_lower_res.png", optimize=True)
make_items(item_sheet, OUT / "textures" / "texture_packs" / "default" / "items")
info_path = OUT / "textures" / "texture_packs" / "default" / "info.json"
info_path.write_text(json.dumps({
    "author": "TyraCraft Portal contributors",
    "title": "Portal Original",
    "description": "Original replacement art for the browser PS2 build",
}, indent=2) + "\n", encoding="utf-8")
make_font(OUT / "textures" / "font" / "ascii.png")

palettes = {
    "steve.png": ((205, 156, 112), (52, 39, 47), (33, 121, 132), (39, 55, 106), (228, 143, 54)),
    "alex.png": ((223, 177, 135), (117, 54, 39), (69, 137, 88), (63, 70, 95), (211, 177, 72)),
    "player.png": ((151, 104, 82), (34, 34, 40), (121, 55, 132), (45, 73, 91), (76, 173, 167)),
    "player2.png": ((229, 190, 145), (219, 196, 111), (48, 87, 122), (78, 55, 91), (205, 77, 61)),
}
for name, palette in palettes.items():
    make_skin(OUT / "textures" / "skin" / name, palette)
make_skin(OUT / "textures" / "entity" / "player" / "steve.png", palettes["steve.png"])
make_skin(OUT / "textures" / "entity" / "pig" / "pig.png", ((214, 135, 143), (151, 74, 91), (224, 154, 160), (181, 96, 111), (247, 190, 168)))
make_environment(OUT / "textures" / "environment")

notices = OUT / "ASSET-NOTICES.md"
notices.write_text(
    "# TyraCraft Portal asset notices\n\n"
    "The original TyraCraft source code is Apache-2.0 licensed. This portal build "
    "does not redistribute the release's Minecraft-derived block atlas, item icons, "
    "character skins, bitmap font, or Mine4K texture pack. Replacement block and "
    "item artwork was generated specifically for this build with OpenAI image "
    "generation and mechanically fitted to TyraCraft's native atlas layout. The "
    "replacement font, skins, and environment textures are original procedural "
    "assets created for this build.\n\n"
    "Silent Wood by Purrple Cat remains under CC BY-SA 3.0; its original LICENSE.txt "
    "is preserved beside the audio file. The MazeCraft Coverless Book track retains "
    "its original Pixabay license certificate.\n",
    encoding="utf-8",
)
print(f"clean assets staged at {OUT}")
