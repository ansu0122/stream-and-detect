from confluent_kafka.admin import AdminClient, NewTopic

def create_topic(broker, topic_name, num_partitions=1, replication_factor=1):
    admin_client = AdminClient({'bootstrap.servers': broker})

    topic_list = [NewTopic(topic_name, num_partitions=num_partitions, replication_factor=replication_factor)]
    fs = admin_client.create_topics(topic_list)

    for topic, f in fs.items():
        try:
            f.result()
            print(f"Topic '{topic}' created successfully.")
        except Exception as e:
            print(f"Failed to create topic '{topic}': {e}")

