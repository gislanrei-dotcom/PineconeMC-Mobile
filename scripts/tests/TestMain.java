public final class TestMain {
    public static void main(String[] args) {
        System.out.println("PINECONE_RUNNER_OK:" + String.join("|", args));
        System.out.println("PINECONE_OPTION:" + System.getProperty("pinecone.test"));
        System.out.println("PINECONE_JAVA_HOME:" + System.getProperty("java.home"));
        System.out.println("PINECONE_NATIVE_PATH:" + System.getProperty("java.library.path"));
        if (args.length == 2 && args[0].equals("coração")) {
            String first = args[0].codePoints().mapToObj(Integer::toHexString)
                .collect(java.util.stream.Collectors.joining(","));
            String second = args[1].codePoints().mapToObj(Integer::toHexString)
                .collect(java.util.stream.Collectors.joining(","));
            System.out.println("PINECONE_UNICODE_CODEPOINTS:" + first + "|" + second);
        }
    }
}
