from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from domains.real_estate.location import normalize_boundary


class BoundaryLocationTests(SimpleTestCase):
    def test_zero_one_two_corners_are_valid(self):
        self.assertEqual(normalize_boundary(None), {})
        self.assertEqual(
            normalize_boundary({"nw": {"lat": 6.5, "lng": 3.3}}),
            {"nw": {"lat": 6.5, "lng": 3.3}},
        )
        self.assertEqual(
            normalize_boundary(
                {
                    "nw": {"lat": 6.5, "lng": 3.3},
                    "se": {"lat": 6.4, "lng": 3.4},
                }
            ),
            {
                "nw": {"lat": 6.5, "lng": 3.3},
                "se": {"lat": 6.4, "lng": 3.4},
            },
        )

    def test_incomplete_and_out_of_range_corner_rejected(self):
        with self.assertRaises(ValidationError):
            normalize_boundary({"nw": {"lat": 6.5}})
        with self.assertRaises(ValidationError):
            normalize_boundary({"nw": {"lat": 91, "lng": 3.3}})
        with self.assertRaises(ValidationError):
            normalize_boundary({"nw": {"lat": 6.5, "lng": 181}})

    def test_legacy_array_is_normalized(self):
        self.assertEqual(
            normalize_boundary(
                [{"lat": 6.5, "lng": 3.3}, {"lat": 6.5, "lng": 3.4}]
            ),
            {
                "nw": {"lat": 6.5, "lng": 3.3},
                "ne": {"lat": 6.5, "lng": 3.4},
            },
        )
