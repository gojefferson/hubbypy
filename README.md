# HubbyPy

`HubbyPy` is a wrapper for HubSpot's contact properties and contacts API. It is particularly useful for web applications where you want to sync information about your users with HubSpot.

## Getting Set Up

```python
hs_user_property_manager = UserPropertyManager(
    groups=[
        {
            'name': 'your_org',
            'displayName': 'Your API Data'
        }
    ]
)

hubspot = HubSpot(
    api_key='add your key here',
    user_property_manager=hs_user_property_manager
)
```

## Accessor Properties

```python
hs_user_property_manager.add_prop(
    AccessorProperty(
        name='email',
        native_type='varchar',
        accessor='email',
        built_in=True
    )
)

hs_user_property_manager.add_prop(
    AccessorProperty(
        name='your_org_company_id',
        label='Your Company: Account id',
        group_name='your_org',
        native_type='varchar',
        accessor='company.id'
    )
)

hs_user_property_manager.add_prop(
    AccessorProperty(
        name='your_org_current_period_end',
        label='Your Company: Subscription End',
        group_name='your_org',
        native_type='datetime',
        accessor='company.stripe_customer.current_subscription.current_period_end'
    )
)
```

## Function Properties
```python
hs_user_property_manager.add_prop(
    FunctionProperty(
        name='your_org_last_sync',
        label='Company: Last Sync',
        group_name='your_org',
        native_type='datetime',
        func=timezone.now,
        send_user=False
    )
)


def get_user_lifecycle_stage(user):
    try:
        if user.company and user.company.stripe_customer.current_subscription.is_trialing:
            return 'opportunity'
        if user.company and user.company.stripe_customer.current_subscription.status == 'active':
            return 'customer'
    except AttributeError as err:
        logger.error('[HUBSPOT] could not get subscription, error: {}'.format(err))
    return 'lead'


hs_user_property_manager.add_prop(
    FunctionProperty(
        name='lifecyclestage',
        native_type='varchar',
        func=get_user_lifecycle_stage,
        send_user=True,
        built_in=True
    )
)
```

## Constant Properties
```python
# Constant Properties
hs_user_property_manager.add_prop(
    ConstantProperty(
        name='your_org_created_by_you',
        label='Your Company: Our App Created',
        group_name='your_org',
        native_type='bool',
        value=True
    )
)
```