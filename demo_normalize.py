"""Quick normalization demo — shows what _normalize does to real student text."""
import sys
sys.path.insert(0, r'C:\dev\kll-lost-and-found')
import matching

examples = [
    "calcu ko po nawala black casio fx 991 may sulat sa likod na BSCS2A pentel pen",
    "scientific calculator itim casio fx991 may sulat sa likod napulot sa lab 2",
    "aquaflask ko nawala blue may sticker ng anime sa gilid medyo malalim ang dent",
    "blue aquaflask may dent sa gilid may anime sticker nakita sa ilalim ng upuan",
    "payong ko po nawala sa hallway black automatic fibrella folding",
    "black automatic na payong fibrella napulot sa hallway",
    "charger ng android ko type-c itim may tape sa dulo ng wire kasi sira medyo",
    "type-c android charger itim may tape sa wire nakita sa plug area ng lab",
    "scical ko white casio fx991 may cover na plastic naiwanan sa room",
    "casio fx991 puti may plastic cover napulot sa mesa",
]

print("=== _normalize() on real Filipino student text ===\n")
for text in examples:
    print(f"IN:  {text}")
    print(f"OUT: {matching._normalize(text)}")
    print()

