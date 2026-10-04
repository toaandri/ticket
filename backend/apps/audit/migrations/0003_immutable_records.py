from django.db import migrations

SQL = """
CREATE FUNCTION ticket_reject_record_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Immutable audit/financial record'; END; $$;
CREATE TRIGGER audit_append_only BEFORE UPDATE OR DELETE ON audit_auditlog
FOR EACH ROW EXECUTE FUNCTION ticket_reject_record_change();
CREATE TRIGGER seat_history_append_only BEFORE UPDATE OR DELETE ON inventory_seatclaimhistory
FOR EACH ROW EXECUTE FUNCTION ticket_reject_record_change();
CREATE TRIGGER order_item_immutable BEFORE UPDATE OR DELETE ON orders_orderitem
FOR EACH ROW EXECUTE FUNCTION ticket_reject_record_change();
CREATE FUNCTION ticket_protect_order() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Financial record cannot be deleted'; END IF;
  IF ROW(NEW.subtotal_minor,NEW.discount_minor,NEW.fees_minor,NEW.tax_minor,NEW.total_minor,NEW.currency,NEW.user_id,NEW.event_id,NEW.reservation_id)
     IS DISTINCT FROM ROW(OLD.subtotal_minor,OLD.discount_minor,OLD.fees_minor,OLD.tax_minor,OLD.total_minor,OLD.currency,OLD.user_id,OLD.event_id,OLD.reservation_id)
  THEN RAISE EXCEPTION 'Order pricing and ownership are immutable'; END IF;
  RETURN NEW;
END; $$;
CREATE TRIGGER order_snapshot_immutable BEFORE UPDATE OR DELETE ON orders_order
FOR EACH ROW EXECUTE FUNCTION ticket_protect_order();
CREATE TRIGGER ticket_no_delete BEFORE DELETE ON tickets_ticket
FOR EACH ROW EXECUTE FUNCTION ticket_reject_record_change();
CREATE TRIGGER payment_no_delete BEFORE DELETE ON payments_paymentattempt
FOR EACH ROW EXECUTE FUNCTION ticket_reject_record_change();
CREATE TRIGGER payment_inbox_no_delete BEFORE DELETE ON payments_paymenteventinbox
FOR EACH ROW EXECUTE FUNCTION ticket_reject_record_change();
CREATE TRIGGER refund_no_delete BEFORE DELETE ON payments_refund
FOR EACH ROW EXECUTE FUNCTION ticket_reject_record_change();
"""
REVERSE = """
DROP TRIGGER audit_append_only ON audit_auditlog;
DROP TRIGGER seat_history_append_only ON inventory_seatclaimhistory;
DROP TRIGGER order_item_immutable ON orders_orderitem;
DROP TRIGGER order_snapshot_immutable ON orders_order;
DROP TRIGGER ticket_no_delete ON tickets_ticket;
DROP TRIGGER payment_no_delete ON payments_paymentattempt;
DROP TRIGGER payment_inbox_no_delete ON payments_paymenteventinbox;
DROP TRIGGER refund_no_delete ON payments_refund;
DROP FUNCTION ticket_reject_record_change();
DROP FUNCTION ticket_protect_order();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0002_auditlog_entity_type_auditlog_event_auditlog_ip_hash_and_more"),
        ("orders", "0001_initial"),
        ("payments", "0001_initial"),
        ("tickets", "0001_initial"),
        ("inventory", "0001_initial"),
    ]
    operations = [migrations.RunSQL(SQL, REVERSE)]
