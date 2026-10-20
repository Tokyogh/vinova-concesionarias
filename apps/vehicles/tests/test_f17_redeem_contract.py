"""ES: Regresiones F17 del formato VNV y canje sin kilometraje del cliente.

EN: F17 regressions for VNV formatting and redemption without client mileage.
"""

import pytest
from django.core.exceptions import ValidationError

from apps.customers.models import Customer
from apps.portal.forms import PortalVehicleRedeemForm
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleLinkCode, VehicleModel
from apps.vehicles.services import redeem_link_code


def test_vnv_form_normalizes_paste_without_hyphens():
    form = PortalVehicleRedeemForm(data={"code": "vnvabcd-efgh-jkmn-pqrs"})

    assert form.is_valid(), form.errors
    assert form.cleaned_data["code"] == "VNV-ABCD-EFGH-JKMN-PQRS"


@pytest.mark.parametrize(
    "value",
    ["ABCDEFGHIJ", "VNV-ABCD-EFGH-JKMN", "VNV-ABCI-EFGH-JKMN-PQRS", "VNV-ABCD-EFGH-JKMN-PQRS-EXTRA"],
)
def test_vnv_form_rejects_noncanonical_issued_contract(value):
    form = PortalVehicleRedeemForm(data={"code": value})

    assert not form.is_valid()
    assert "code" in form.errors


@pytest.mark.django_db
def test_redeem_uses_authorized_vehicle_mileage_or_keeps_it_unknown():
    brand = VehicleBrand.objects.create(name="Marca Pruebas")
    model = VehicleModel.objects.create(brand=brand, name="Modelo Pruebas")
    vehicle = Vehicle.objects.create(
        brand=brand,
        model=model,
        year=2026,
        public_slug="vehiculo-sin-kilometraje",
        mileage=None,
    )
    customer = Customer.objects.create(first_name="Cliente", last_name="Pruebas")
    code = VehicleLinkCode.objects.create(vehicle=vehicle, code=VehicleLinkCode.generate_new_code())

    link = redeem_link_code(customer=customer, code=code.code)

    assert link.initial_mileage is None
    assert link.vehicle.mileage is None


def test_model_normalizer_rejects_unknown_alphabet_character():
    with pytest.raises(ValidationError):
        VehicleLinkCode.normalize_input("VNV-ABCI-EFGH-JKMN-PQRS")
