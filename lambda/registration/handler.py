"""
Registration Lambda -- Triple Point SU26 Final Project (Group 4).
 
Triggered by EventBridge on CloudTrail resource-creation events.
 
Responsibilities in the T05 baseline:
  1. Identify the AWS identity that made the API call.
  2. Extract the resource identifiers that were created.
  3. Build an ownership record.
  4. Publish a human-readable notification to SNS.
 
Deliberately uses ONLY boto3 and the standard library. boto3 ships in the
Lambda Python runtime, so there is no dependency packaging, no Lambda layer,
and no Docker build step. Keep it that way.
 
Next increments (do not add these until the baseline is proven end to end):
  T13 - enrich the record from AWS Config (get_resource_config_history)
  T14 - persist build_ownership_record() output to DynamoDB
"""
 
import json
import logging
import os
from datetime import datetime, timezone
 
import boto3
 
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
 
sns = boto3.client("sns")
 
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
 
# Maps a CloudTrail eventName to (resource_type, extractor function name).
# Adding a resource type for T23/T24 means adding a row here and adding the
# eventName to var.tracked_event_names. Nothing else changes.
SUPPORTED_EVENTS = {
    "RunInstances": "AWS::EC2::Instance",
    "CreateVpc": "AWS::EC2::VPC",
    "CreateSubnet": "AWS::EC2::Subnet",
    "CreateCustomerGateway": "AWS::EC2::CustomerGateway",
    "CreateVpnGateway": "AWS::EC2::VPNGateway",
    "CreateVpnConnection": "AWS::EC2::VPNConnection",
}
 
# Risk tiers. This is a placeholder so the baseline runs end to end -- the
# Lifecycle team owns the real matrix (T08/T17). Keep it as data, not as
# if/else logic buried in a function, so it can move to a config file and be
# lifted straight into the consulting report as a table.
RISK_BY_TYPE = {
    "AWS::EC2::Instance": "HIGH",
    "AWS::EC2::VPNConnection": "HIGH",
    "AWS::EC2::VPNGateway": "MEDIUM",
    "AWS::EC2::CustomerGateway": "LOW",
    "AWS::EC2::VPC": "LOW",
    "AWS::EC2::Subnet": "LOW",
}
DEFAULT_RISK = "MEDIUM"
 
 
def extract_identity(user_identity):
    """
    Resolve a CloudTrail userIdentity block to a human-attributable principal.
 
    CloudTrail represents the same human differently depending on how they
    authenticated, which is the single most annoying part of this project.
    Handles the three cases you will actually see in a training account.
    """
    identity_type = user_identity.get("type", "Unknown")
    arn = user_identity.get("arn", "")
 
    if identity_type == "IAMUser":
        principal = user_identity.get("userName") or arn.split("/")[-1]
 
    elif identity_type == "AssumedRole":
        # arn looks like:
        #   arn:aws:sts::123456789012:assumed-role/RoleName/session-name
        # The session name is usually the human (SSO username, or the name the
        # intern passed to assume-role). Fall back to the role name.
        session_context = user_identity.get("sessionContext", {})
        session_issuer = session_context.get("sessionIssuer", {})
        role_name = session_issuer.get("userName", "UnknownRole")
        session_name = arn.split("/")[-1] if "/" in arn else "UnknownSession"
        principal = f"{role_name}/{session_name}"
 
    elif identity_type == "Root":
        principal = "root"
 
    else:
        principal = arn or identity_type
 
    return {
        "principal": principal,
        "identity_type": identity_type,
        "arn": arn,
        "account_id": user_identity.get("accountId", "unknown"),
        "principal_id": user_identity.get("principalId", "unknown"),
    }
 
 
def extract_resource_ids(event_name, response_elements):
    """
    Pull the created resource IDs out of the CloudTrail responseElements.
 
    Returns a list because RunInstances can create several instances in one
    call -- an intern launching 3 instances must produce 3 ownership records,
    not 1.
    """
    if not response_elements:
        return []
 
    if event_name == "RunInstances":
        items = response_elements.get("instancesSet", {}).get("items", [])
        return [i["instanceId"] for i in items if "instanceId" in i]
 
    if event_name == "CreateVpc":
        vpc = response_elements.get("vpc", {})
        return [vpc["vpcId"]] if "vpcId" in vpc else []
 
    if event_name == "CreateSubnet":
        subnet = response_elements.get("subnet", {})
        return [subnet["subnetId"]] if "subnetId" in subnet else []
 
    if event_name == "CreateCustomerGateway":
        cgw = response_elements.get("customerGateway", {})
        return [cgw["customerGatewayId"]] if "customerGatewayId" in cgw else []
 
    if event_name == "CreateVpnGateway":
        vgw = response_elements.get("vpnGateway", {})
        return [vgw["vpnGatewayId"]] if "vpnGatewayId" in vgw else []
 
    if event_name == "CreateVpnConnection":
        vpn = response_elements.get("vpnConnection", {})
        return [vpn["vpnConnectionId"]] if "vpnConnectionId" in vpn else []
 
    return []
 
 
def build_ownership_record(resource_id, resource_type, identity, detail):
    """
    The ownership record. THIS IS THE FROZEN CONTRACT between the Registration
    team and the Lifecycle team -- do not change these keys without telling
    everyone, because the lifecycle Lambda reads them.
 
    In T14 this dict becomes the DynamoDB item, with resource_id as the
    partition key.
    """
    return {
        "resource_id": resource_id,
        "resource_type": resource_type,
        "owner_principal": identity["principal"],
        "owner_arn": identity["arn"],
        "owner_identity_type": identity["identity_type"],
        "created_at": detail.get("eventTime", datetime.now(timezone.utc).isoformat()),
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "region": detail.get("awsRegion", "unknown"),
        "account_id": identity["account_id"],
        "event_name": detail.get("eventName", "unknown"),
        "source_ip": detail.get("sourceIPAddress", "unknown"),
        "risk_tier": RISK_BY_TYPE.get(resource_type, DEFAULT_RISK),
        "last_notified_at": None,
        "review_status": "ACTIVE",
    }
 
 
def format_notification(records):
    """Human-readable SNS body. Owners read this, so keep it plain."""
    lines = [
        "AWS Resource Registration",
        "=" * 40,
        "",
        f"{len(records)} resource(s) registered.",
        "",
    ]
 
    for record in records:
        lines.extend(
            [
                f"Resource ID:   {record['resource_id']}",
                f"Type:          {record['resource_type']}",
                f"Owner:         {record['owner_principal']}",
                f"Owner ARN:     {record['owner_arn']}",
                f"Created:       {record['created_at']}",
                f"Region:        {record['region']}",
                f"Risk tier:     {record['risk_tier']}",
                f"API call:      {record['event_name']}",
                "-" * 40,
            ]
        )
 
    lines.extend(
        [
            "",
            "This resource is now tracked for lifecycle review.",
            "This system does not delete resources. You remain responsible for cleanup.",
        ]
    )
 
    return "\n".join(lines)
 
 
def lambda_handler(event, context):
    # Log the raw event during the baseline. It is how you learn the real event
    # shape, and it is how you build the sample JSON fixtures the Lifecycle team
    # develops against without needing AWS access.
    logger.info("Raw event: %s", json.dumps(event))
 
    detail = event.get("detail", {})
    event_name = detail.get("eventName", "")
 
    if event_name not in SUPPORTED_EVENTS:
        logger.warning("Unsupported eventName '%s' -- ignoring.", event_name)
        return {"status": "ignored", "reason": f"unsupported event {event_name}"}
 
    if detail.get("errorCode"):
        logger.warning("API call failed (%s) -- ignoring.", detail["errorCode"])
        return {"status": "ignored", "reason": "failed API call"}
 
    resource_type = SUPPORTED_EVENTS[event_name]
    identity = extract_identity(detail.get("userIdentity", {}))
    resource_ids = extract_resource_ids(event_name, detail.get("responseElements"))
 
    if not resource_ids:
        logger.warning("No resource IDs found in responseElements for %s.", event_name)
        return {"status": "ignored", "reason": "no resource IDs in event"}
 
    records = [
        build_ownership_record(rid, resource_type, identity, detail)
        for rid in resource_ids
    ]
 
    for record in records:
        logger.info("Ownership record: %s", json.dumps(record))
        # T14: dynamodb.put_item(TableName=..., Item=to_dynamo(record))
 
    subject = f"[Resource Registered] {len(records)} x {resource_type.split('::')[-1]}"
 
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=subject[:100],  # SNS hard-limits Subject to 100 characters
        Message=format_notification(records),
    )
 
    logger.info("Published notification for %d resource(s).", len(records))
 
    return {
        "status": "registered",
        "count": len(records),
        "resource_ids": [r["resource_id"] for r in records],
    }
    """