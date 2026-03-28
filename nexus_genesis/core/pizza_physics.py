import math

class ThicknessSavant:
    
    @staticmethod
    def calculate_thickness_factor(dough_weight_grams, diameter_inches):
        """
        Calculates the thickness factor (TF) given dough weight and pizza diameter.
        
        Parameters:
        - dough_weight_grams: weight of the dough in grams
        - diameter_inches: diameter of the pizza in inches
        
        Returns:
        - thickness factor (TF)
        """
        radius_inches = diameter_inches / 2
        area_square_inches = math.pi * (radius_inches ** 2)
        return dough_weight_grams / area_square_inches

    @staticmethod
    def predict_dough_weight(target_tf, diameter_inches):
        """
        Predicts the required dough weight for a given thickness factor and pizza diameter.
        
        Parameters:
        - target_tf: desired thickness factor
        - diameter_inches: diameter of the pizza in inches
        
        Returns:
        - predicted dough weight in grams
        """
        radius_inches = diameter_inches / 2
        area_square_inches = math.pi * (radius_inches ** 2)
        return target_tf * area_square_inches

    @staticmethod
    def validate():
        """
        Validates the calculations against specific data points.
        """
        # Example data points (diameter in inches, dough weight in grams, expected TF)
        data_points = [
            (14, 453.6, 0.080),
            # Add more data points as needed
            # (diameter, dough_weight, expected_tf)
        ]
        
        for diameter, dough_weight, expected_tf in data_points:
            calculated_tf = ThicknessSavant.calculate_thickness_factor(dough_weight, diameter)
            assert math.isclose(calculated_tf, expected_tf, rel_tol=1e-3), \
                f"Validation failed for diameter {diameter} and dough weight {dough_weight}."

if __name__ == "__main__":
    ThicknessSavant.validate()
    print("All validations passed!")