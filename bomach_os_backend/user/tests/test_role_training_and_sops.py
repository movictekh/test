import json
from django.test import TestCase

from user.models.role_sop import RoleSOP
from user.models.role_training_requirements import RoleTrainingRequirement
from user.tests.helpers import (
    RoleAPITestMixin,
    SOPFactoryMixin,
    TrainingProgramFactoryMixin,
)


class RoleTrainingRequirementAPITests(
    RoleAPITestMixin, TrainingProgramFactoryMixin, TestCase
):
    def test_can_create_list_and_patch_role_training_requirements(self):
        admin_role = self.create_role(
            "Training Requirement Admin",
            {"role_training_requirements": ["create", "list", "update"]},
        )
        admin = self.create_user_with_employee(
            email="training-admin@example.com",
            username="trainingadmin",
            employee_id="EMP-TRAINING-ADMIN",
            role=admin_role,
        )
        target_role = self.create_role("Sales Executive", {})
        training_program = self.create_training_program("Bomach OS Training")

        payload = {
            "training_program_id": training_program.id,
            "requirement_type": "mandatory",
        }
        response = self.client.post(
            f"/api/v1/roles/{target_role.id}/training-requirements",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 201)
        created = response.json()
        self.assertEqual(created["training_program_id"], training_program.id)
        self.assertEqual(
            created["training_program"]["program_name"], training_program.program_name
        )
        self.assertEqual(created["requirement_type"], "mandatory")
        self.assertEqual(created["sequence"], 1)

        response = self.client.get(
            f"/api/v1/roles/{target_role.id}/training-requirements?requirement_type=mandatory&training_program_id={training_program.id}&search=bomach&is_active=true",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(
            data["items"][0]["training_program"]["provider"], training_program.provider
        )

        next_program = self.create_training_program(
            "Sales Training", provider="External Vendor"
        )
        response = self.client.patch(
            f"/api/v1/roles/{target_role.id}/training-requirements/{created['id']}",
            data=json.dumps(
                {
                    "training_program_id": next_program.id,
                    "requirement_type": "continuous",
                    "is_active": False,
                }
            ),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        updated = response.json()
        self.assertEqual(updated["training_program_id"], next_program.id)
        self.assertEqual(updated["requirement_type"], "continuous")
        self.assertFalse(updated["is_active"])

    def test_employee_can_list_own_training_requirements(self):
        employee_role = self.create_role(
            "Sales Executive",
            {"role_training_requirements": ["list_own"]},
        )
        employee = self.create_user_with_employee(
            email="training-user@example.com",
            username="traininguser",
            employee_id="EMP-TRAINING-USER",
            role=employee_role,
        )
        training_program = self.create_training_program("Bomach OS Training")
        RoleTrainingRequirement.objects.create(
            role=employee_role,
            training_program=training_program,
            requirement_type="mandatory",
            sequence=1,
        )

        response = self.client.get(
            "/api/v1/roles/me/training-requirements",
            **self.auth_headers(employee),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(
            data["items"][0]["training_program"]["program_name"], "Bomach OS Training"
        )

    def test_employee_can_get_grouped_own_training_requirements(self):
        employee_role = self.create_role(
            "Sales Executive",
            {"role_training_requirements": ["list_own"]},
        )
        employee = self.create_user_with_employee(
            email="training-grouped@example.com",
            username="traininggrouped",
            employee_id="EMP-TRAINING-GROUPED",
            role=employee_role,
        )
        mandatory_program = self.create_training_program("Bomach OS Training")
        continuous_program = self.create_training_program("Sales Training")
        RoleTrainingRequirement.objects.create(
            role=employee_role,
            training_program=mandatory_program,
            requirement_type="mandatory",
            sequence=1,
        )
        RoleTrainingRequirement.objects.create(
            role=employee_role,
            training_program=continuous_program,
            requirement_type="continuous",
            sequence=2,
        )

        response = self.client.get(
            "/api/v1/roles/me/training-requirements/grouped",
            **self.auth_headers(employee),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["mandatory"]), 1)
        self.assertEqual(
            data["mandatory"][0]["training_program"]["program_name"],
            "Bomach OS Training",
        )
        self.assertEqual(len(data["continuous"]), 1)
        self.assertEqual(
            data["continuous"][0]["training_program"]["program_name"], "Sales Training"
        )

    def test_training_requirement_sequence_auto_increments_when_omitted(self):
        admin_role = self.create_role(
            "Training Requirement Admin",
            {"role_training_requirements": ["create"]},
        )
        admin = self.create_user_with_employee(
            email="training-seq@example.com",
            username="trainingseq",
            employee_id="EMP-TRAINING-SEQ",
            role=admin_role,
        )
        target_role = self.create_role("Sales Executive", {})
        first_program = self.create_training_program("Bomach OS Training")
        second_program = self.create_training_program("Sales Training")

        first_response = self.client.post(
            f"/api/v1/roles/{target_role.id}/training-requirements",
            data=json.dumps(
                {
                    "training_program_id": first_program.id,
                    "requirement_type": "mandatory",
                }
            ),
            content_type="application/json",
            **self.auth_headers(admin),
        )
        second_response = self.client.post(
            f"/api/v1/roles/{target_role.id}/training-requirements",
            data=json.dumps(
                {
                    "training_program_id": second_program.id,
                    "requirement_type": "continuous",
                }
            ),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(first_response.json()["sequence"], 1)
        self.assertEqual(second_response.json()["sequence"], 2)

    def test_requirement_type_is_required_when_creating_training_requirement(self):
        admin_role = self.create_role(
            "Training Requirement Admin",
            {"role_training_requirements": ["create"]},
        )
        admin = self.create_user_with_employee(
            email="training-required@example.com",
            username="trainingrequired",
            employee_id="EMP-TRAINING-REQ",
            role=admin_role,
        )
        target_role = self.create_role("Sales Executive", {})
        training_program = self.create_training_program("Bomach OS Training")

        response = self.client.post(
            f"/api/v1/roles/{target_role.id}/training-requirements",
            data=json.dumps({"training_program_id": training_program.id}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 422)


class RoleSOPAPITests(RoleAPITestMixin, SOPFactoryMixin, TestCase):
    def test_can_create_list_and_patch_role_sops(self):
        admin_role = self.create_role(
            "Role SOP Admin",
            {"role_sops": ["create", "list", "update"]},
        )
        admin = self.create_user_with_employee(
            email="rolesop-admin@example.com",
            username="rolesopadmin",
            employee_id="EMP-ROLESOP-ADMIN",
            role=admin_role,
        )
        target_role = self.create_role("Field Officer", {})
        sop = self.create_sop("Client Land Purchase Process")

        payload = {
            "sop_id": sop.id,
            "is_active": True,
        }
        response = self.client.post(
            f"/api/v1/roles/{target_role.id}/sops",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 201)
        created = response.json()
        self.assertEqual(created["sop_id"], sop.id)
        self.assertEqual(created["sop"]["title"], sop.title)

        response = self.client.get(
            f"/api/v1/roles/{target_role.id}/sops?priority=High&search=land&is_active=true&is_up_to_date=true&sop_id={sop.id}",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["items"][0]["sop"]["version"], "v1.0")

        next_sop = self.create_sop("Allocation Procedure", priority="Medium")
        response = self.client.patch(
            f"/api/v1/roles/{target_role.id}/sops/{created['id']}",
            data=json.dumps({"sop_id": next_sop.id, "is_active": False}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        updated = response.json()
        self.assertEqual(updated["sop_id"], next_sop.id)
        self.assertFalse(updated["is_active"])

    def test_employee_can_list_own_role_sops(self):
        employee_role = self.create_role(
            "Field Officer",
            {"role_sops": ["list_own"]},
        )
        employee = self.create_user_with_employee(
            email="rolesop-user@example.com",
            username="rolesopuser",
            employee_id="EMP-ROLESOP-USER",
            role=employee_role,
        )
        sop = self.create_sop("Client Land Purchase Process")
        RoleSOP.objects.create(
            role=employee_role,
            sop=sop,
            is_active=True,
        )

        response = self.client.get(
            "/api/v1/roles/me/sops",
            **self.auth_headers(employee),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["items"][0]["sop"]["title"], sop.title)

    def test_duplicate_role_sop_link_is_rejected(self):
        admin_role = self.create_role(
            "Role SOP Admin",
            {"role_sops": ["create"]},
        )
        admin = self.create_user_with_employee(
            email="rolesop-dupe@example.com",
            username="rolesopdupe",
            employee_id="EMP-ROLESOP-DUPE",
            role=admin_role,
        )
        target_role = self.create_role("Field Officer", {})
        sop = self.create_sop("Client Land Purchase Process")

        first_response = self.client.post(
            f"/api/v1/roles/{target_role.id}/sops",
            data=json.dumps({"sop_id": sop.id}),
            content_type="application/json",
            **self.auth_headers(admin),
        )
        second_response = self.client.post(
            f"/api/v1/roles/{target_role.id}/sops",
            data=json.dumps({"sop_id": sop.id}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 400)
